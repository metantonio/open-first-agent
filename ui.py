import chainlit as cl
from universal_orchestrator import orchestrator
import logging
import sys
import re
import asyncio
import subprocess
import platform
import os
from typing import Optional
import paramiko
import json
from datetime import datetime
from chainlit.types import ThreadDict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('agent.log')
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(ch)

# Global variables for terminal state
class TerminalState:
    def __init__(self):
        self.current_directory: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        self.history: list = []
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.ssh_info: Optional[dict] = None
        self.prompt: str = "$ "
        os.makedirs(self.current_directory, exist_ok=True)

    def is_ssh_connected(self) -> bool:
        return self.ssh_client is not None and self.ssh_client.get_transport() is not None and self.ssh_client.get_transport().is_active()

    def update_prompt(self):
        if self.is_ssh_connected():
            self.prompt = f"{self.ssh_info['username']}@{self.ssh_info['hostname']}:{self.current_directory}$ "
        else:
            self.prompt = f"local:{self.current_directory}$ "

    async def connect_ssh(self, hostname: str, username: str, password: str = None, key_path: str = None) -> bool:
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if key_path:
                self.ssh_client.connect(hostname, username=username, key_filename=key_path)
            else:
                self.ssh_client.connect(hostname, username=username, password=password)
            
            self.ssh_info = {
                'hostname': hostname,
                'username': username,
                'connected_at': datetime.now().isoformat(),
                'using_key': key_path is not None
            }
            self.update_prompt()
            return True
        except Exception as e:
            logger.error(f"SSH connection failed: {str(e)}")
            self.ssh_client = None
            self.ssh_info = None
            return False

    def disconnect_ssh(self):
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
            self.ssh_info = None
            self.update_prompt()

# Initialize terminal state
terminal = TerminalState()

def get_background_command(command: str) -> str:
    """Get the appropriate background command format for the current OS."""
    os_name = platform.system().lower()
    
    if os_name == "windows":
        # Windows: use 'start /B' for background processes
        return f"start /B {command} > NUL 2>&1"
    else:
        # Unix-like systems (Linux, macOS): use nohup
        return f"nohup {command} > /dev/null 2>&1 &"

def get_shell_info() -> tuple[bool, str]:
    """Get shell information based on the OS."""
    os_name = platform.system().lower()
    
    if os_name == "windows":
        return True, "cmd.exe"  # shell=True and use cmd.exe
    else:
        return True, "/bin/sh"  # shell=True and use sh

def get_working_directory(command: str) -> str:
    """Determine the appropriate working directory for a command."""
    if terminal.current_directory is None:
        # Initialize with output directory if not set
        terminal.current_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        os.makedirs(terminal.current_directory, exist_ok=True)
    
    return terminal.current_directory

async def execute_command(command: str, is_background: bool = False, working_dir: str = None) -> str:
    """Execute a shell command and return the output."""
    try:
        use_shell, shell_exe = get_shell_info()
        
        # Handle cd command specially
        if command.strip().startswith('cd '):
            new_dir = command.strip()[3:].strip()
            if new_dir:
                if os.path.isabs(new_dir):
                    target_dir = new_dir
                else:
                    target_dir = os.path.abspath(os.path.join(terminal.current_directory, new_dir))
                
                if os.path.exists(target_dir) and os.path.isdir(target_dir):
                    terminal.current_directory = target_dir
                    return f"Changed directory to: {terminal.current_directory}"
                else:
                    return f"Directory not found: {new_dir}"
        
        # Use terminal.current_directory if working_dir not specified
        cwd = working_dir if working_dir else terminal.current_directory
        
        if is_background:
            # Format command for background execution based on OS
            bg_command = get_background_command(command)
            process = await asyncio.create_subprocess_shell(
                bg_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=use_shell,
                executable=shell_exe,
                cwd=cwd
            )
            return f"Command started in background in directory: {cwd}"
        else:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=use_shell,
                executable=shell_exe,
                cwd=cwd
            )
            stdout, stderr = await process.communicate()
            
            # Add command to terminal history
            terminal.history.append({
                'command': command,
                'output': stdout.decode() if process.returncode == 0 else stderr.decode(),
                'success': process.returncode == 0
            })
            
            if process.returncode == 0:
                return f"Working directory: {cwd}\nOutput:\n{stdout.decode()}"
            else:
                return f"Error in directory {cwd}:\n{stderr.decode()}"
    except Exception as e:
        return f"Failed to execute command: {str(e)}"

def process_code_blocks(content: str) -> tuple[str, list[dict]]:
    """Process content to find code blocks with run tags and create Chainlit elements."""
    command_blocks = []
    
    # Pattern to match code blocks with {run}, {run:background}, or {run_N} tags
    pattern = r"```bash\s*{(run(?::\w+)?(?:_\d+)?)}(.*?)```"
    
    def create_command_block(code: str, tag: str) -> dict:
        """Create a command block with its associated elements."""
        code = code.strip()
        
        # Clean up the command - remove any transfer_to_*_agent wrapper
        code = re.sub(r'transfer_to_\w+_agent\((.*?)\)', r'\1', code)
        # Remove any JSON-like wrapper and extract the actual command
        code = re.sub(r'^\s*{\s*"[^"]+"\s*:\s*"([^"]+)"\s*}\s*$', r'\1', code)
        
        is_background = ":background" in tag
        working_dir = get_working_directory(code)
        
        return {
            'code': code,
            'is_background': is_background,
            'working_dir': working_dir,
            'action_id': "run"  # Always use "run" as the action_id
        }
    
    def replacement(match):
        tag, code = match.groups()
        
        # Create command block
        command_block = create_command_block(code, tag)
        command_blocks.append(command_block)
        
        # Return empty string as we'll handle the display separately
        return ""
    
    # Process all code blocks
    content_without_commands = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    return content_without_commands, command_blocks

async def update_terminal_display():
    """Update the terminal display with current state and history."""
    # Create terminal content
    terminal_content = [
        "```terminal",
        f"Current Directory: {terminal.current_directory}",
        "Recent Commands:",
        "-------------------"
    ]
    
    # Add command history
    for entry in terminal.history[-10:]:  # Show last 10 commands
        terminal_content.append(f"$ {entry['command']}")
        if entry['output']:
            terminal_content.append(entry['output'])
    
    terminal_content.append("```")
    
    # Create terminal message
    terminal_msg = cl.Message(content="\n".join(terminal_content))
    await terminal_msg.send()

@cl.action_callback("run")
async def on_action(action: cl.Action):
    """Handle execution of code blocks when action buttons are clicked."""
    try:
        # Get command from either value or payload
        command = action.value if hasattr(action, 'value') else action.payload.get("command")
        if not command:
            raise ValueError("No command found in action")
            
        payload = action.payload or {}
        is_background = payload.get("is_background", False)
        working_dir = payload.get("working_dir")
        
        # Clean up the command if needed
        command = re.sub(r'transfer_to_\w+_agent\((.*?)\)', r'\1', command)
        command = re.sub(r'^\s*{\s*"[^"]+"\s*:\s*"([^"]+)"\s*}\s*$', r'\1', command)
        
        # Send execution message
        await cl.Message(
            content=f"💻 Executing: `{command}` in {os.path.basename(working_dir)}"
        ).send()
        
        # Execute the command
        result = await execute_command(command, is_background, working_dir)
        
        # Update terminal display
        await update_terminal_display()
        
        # Send the result
        if result.strip():
            await cl.Message(
                content=f"📝 Output:\n```\n{result}\n```"
            ).send()
        else:
            await cl.Message(content="✅ Command executed successfully (no output)").send()
    except Exception as e:
        await cl.Message(content=f"❌ Error executing command: {str(e)}").send()

@cl.on_chat_start
async def start():
    """Function that runs when a new chat session starts."""
    # Initialize session state
    cl.user_session.set('mode', 'chat')
    
    # Create menu options
    menu_actions = [
        cl.Action(
            name="open_terminal",
            value="terminal",
            description="Open Terminal Interface",
            payload={"action": "open_terminal"}
        )
    ]
    
    # Send welcome message with menu options
    await cl.Message(
        content="""👋 Welcome to the AI Assistant!

I can help you with various tasks:

1. 🌐 Web Search and News
2. 🏗️ Terraform Infrastructure
3. 💻 Development Environment Setup
4. ☁️ AWS CLI Configuration
5. 📂 File System Operations
6. 🖥️ Terminal Interface

Menu Options:
- Click the Terminal button or type 'terminal' to open Terminal Interface (terminal mode)
- Type your request for AI assistance
- Execute commands in the chat mode using the ! prefix

What would you like to do?""",
        actions=menu_actions,
        author="AI Assistant"
    ).send()

@cl.action_callback("open_terminal")
async def on_terminal_open(action: cl.Action):
    """Handle terminal open request."""
    try:
        cl.user_session.set('mode', 'terminal')
        await create_terminal_interface()
    except Exception as e:
        await cl.Message(content=f"❌ Error opening terminal: {str(e)}").send()

async def create_terminal_interface(settings: dict = None):
    """Create and display the terminal interface."""
    terminal_content = f"""```terminal
╔══════════════════════════════════════════════════════════════════════════════
║ 🖥️  Terminal Interface
║══════════════════════════════════════════════════════════════════════════════
║ Current Directory: {terminal.current_directory}
║
║ Available Commands:
║ - Type 'clear' to clear the terminal
║ - Type 'cd <directory>' to change directory
║ - Type 'ssh connect' to establish SSH connection
║ - Type 'ssh disconnect' to close SSH connection
║ - Type 'exit' to return to chat mode
║══════════════════════════════════════════════════════════════════════════════
"""

    # Send terminal interface
    await cl.Message(content=terminal_content).send()
    
    # Show command history if any
    if terminal.history:
        history = "\n".join([
            "Recent Commands:",
            "══════════════",
            *[f"$ {entry['command']}\n{entry['output'] if entry['output'] else '(no output)'}" 
              for entry in terminal.history[-5:]],
            "══════════════"
        ])
        await cl.Message(content=f"```terminal\n{history}\n```").send()
    
    # Show current prompt
    await cl.Message(content=f"```terminal\n{terminal.prompt}```").send()

@cl.on_message
async def main(message: cl.Message):
    """Main function to handle user messages and route them to appropriate agents."""
    request = message.content.strip()
    
    # Get current session state
    mode = cl.user_session.get('mode', 'chat')
    
    # Handle menu navigation
    if request.lower() == "terminal":
        cl.user_session.set('mode', 'terminal')
        await create_terminal_interface()
        return
    
    # Handle terminal commands when in terminal mode
    if mode == 'terminal':
        if request.lower() == 'exit':
            cl.user_session.set('mode', 'chat')
            await cl.Message(content="Exited terminal mode. Back to chat mode.").send()
            return
            
        if request.lower() == 'clear':
            await create_terminal_interface()
            return
            
        if request.startswith('ssh'):
            parts = request.split()
            if len(parts) < 2:
                await cl.Message(content="Invalid SSH command. Usage:\n- ssh connect hostname username [--key /path/to/key.pem]\n- ssh disconnect").send()
                return
                
            if parts[1] == 'connect':
                if len(parts) < 4:
                    await cl.Message(content="Invalid SSH connect command. Usage: ssh connect hostname username [--key /path/to/key.pem]").send()
                    return

                hostname = parts[2]
                username = parts[3]
                key_path = None
                password = None

                # Check for key file
                if len(parts) > 4 and parts[4] == '--key' and len(parts) > 5:
                    key_path = parts[5]
                else:
                    # If no key specified, prompt for password
                    await cl.Message(content="Please enter your password in the next message:").send()
                    password_msg = await cl.Message.get_next()
                    password = password_msg.content

                success = await terminal.connect_ssh(
                    hostname=hostname,
                    username=username,
                    password=password,
                    key_path=key_path
                )
                
                if success:
                    await cl.Message(content="✅ SSH connection established!").send()
                else:
                    await cl.Message(content="❌ Failed to establish SSH connection.").send()
                
                await create_terminal_interface()
                return
                
            elif parts[1] == 'disconnect':
                terminal.disconnect_ssh()
                await cl.Message(content="✅ SSH connection closed.").send()
                await create_terminal_interface()
                return
        
        # Execute command and update terminal
        result = await execute_command(request)
        terminal.update_prompt()
        
        # Show command output with proper formatting
        if result.strip():
            await cl.Message(content=f"```terminal\n{result}\n```").send()
        
        # Show new prompt
        await cl.Message(content=f"```terminal\n{terminal.prompt}```").send()
        return
    
    # Handle normal chat mode
    # Check if it's a direct terminal command (starts with !)
    if request.startswith('!'):
        command = request[1:].strip()
        result = await execute_command(command)
        await update_terminal_display()
        await cl.Message(content=f"📝 Output:\n```\n{result}\n```").send()
        return
    
    # Special handling for command examples
    if request.lower().strip() in ['show command ls examples']:
        # Send example message
        await cl.Message(content="Here are some example commands you can try:").send()
        
        # Test commands
        test_commands = [
            {
                'command': 'ls -la',
                'dir': 'output'
            },
            {
                'command': 'terraform --version',
                'dir': 'terraform'
            }
        ]
        
        # Send each test command
        for i, cmd in enumerate(test_commands):
            action = cl.Action(
                name=f"run_{i}",
                value=cmd['command'],
                description=f"Execute in {cmd['dir']} directory",
                payload={
                    "command": cmd['command'],
                    "working_dir": get_working_directory(cmd['command']),
                    "is_background": False
                }
            )
            
            msg = cl.Message(
                content=f"Example {i+1}: `{cmd['command']}` (in {cmd['dir']} directory)",
                actions=[action]
            )
            await msg.send()
        
        return

    # Normal request processing
    msg = cl.Message(
        content=f"🤔 Processing your request: '{request}'...\nThis may take a few moments."
    )
    await msg.send()
    
    try:
        # Process the request using the universal orchestrator
        response = await orchestrator.process_request(request)
        
        # Process the response for executable code blocks
        content, command_blocks = process_code_blocks(response)
        
        # If we have commands to display
        if command_blocks:
            # First send the main content if any
            if content.strip():
                await cl.Message(content=content).send()
            
            # Then send each command block
            for i, cmd_block in enumerate(command_blocks):
                action = cl.Action(
                    name=cmd_block['action_id'],
                    value=cmd_block['code'],
                    description=f"Execute in {os.path.basename(cmd_block['working_dir'])}",
                    payload={
                        "command": cmd_block['code'],
                        "is_background": cmd_block['is_background'],
                        "working_dir": cmd_block['working_dir']
                    }
                )
                
                msg = cl.Message(
                    content=f"Command {i+1}: `{cmd_block['code']}` (in {os.path.basename(cmd_block['working_dir'])})",
                    actions=[action]
                )
                await msg.send()
            
            # Update terminal display after processing commands
            await update_terminal_display()
        else:
            # If no commands, just send the content
            await cl.Message(content=response).send()
            
    except Exception as e:
        error_message = f"❌ Sorry, I encountered an error: {str(e)}"
        if "429" in str(e):
            error_message += "\nIt seems we've hit an API rate limit. Please try again in a few minutes."
        await cl.Message(content=error_message).send() 