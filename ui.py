import chainlit as cl
from universal_orchestrator import orchestrator
import logging
import sys
import re
import asyncio
import os
from terminal_manager import terminal_manager
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
        working_dir = terminal_manager.get_working_directory(code)
        
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
    # Get terminal content from manager
    terminal_content = terminal_manager.create_terminal_content()
    
    # Create terminal message
    terminal_msg = cl.Message(content=terminal_content)
    await terminal_msg.send()
    
    # Show command history if any
    history_content = terminal_manager.get_history_content()
    if history_content:
        await cl.Message(content=history_content).send()

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
        
        # Execute the command using terminal manager
        result = await terminal_manager.execute_command(command, is_background, working_dir)
        
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
    # Get terminal content from manager
    terminal_content = terminal_manager.create_terminal_content()
    await cl.Message(content=terminal_content).send()
    
    # Show command history if any
    history_content = terminal_manager.get_history_content()
    if history_content:
        await cl.Message(content=history_content).send()
    
    # Show current prompt
    await cl.Message(content=f"```terminal\n{terminal_manager.terminal.prompt}```").send()

async def handle_ssh_connection(message):
    """Handle SSH connection with proper user input handling"""
    try:
        # Ask for connection details
        await cl.Message(content="Please provide SSH connection details:").send()
        
        # Get hostname
        hostname = await cl.AskUserMessage(
            content="Enter hostname (e.g., example.com):",
            timeout=180
        ).send()
        
        if not hostname:
            await cl.Message(content="Connection cancelled - no hostname provided").send()
            return
            
        # Get username
        username = await cl.AskUserMessage(
            content="Enter username:",
            timeout=180
        ).send()
        
        if not username:
            await cl.Message(content="Connection cancelled - no username provided").send()
            return
            
        # Ask for authentication method
        auth_method = await cl.AskUserMessage(
            content="Choose authentication method (password/key):",
            timeout=180
        ).send()
        
        if not auth_method or auth_method.lower() not in ['password', 'key']:
            await cl.Message(content="Invalid authentication method. Please use 'password' or 'key'").send()
            return
            
        if auth_method.lower() == 'password':
            # Get password
            password = await cl.AskUserMessage(
                content="Enter password:",
                timeout=180,
                password=True  # This will mask the password input
            ).send()
            
            if not password:
                await cl.Message(content="Connection cancelled - no password provided").send()
                return
                
            # Connect with password
            result = await terminal_manager.terminal.connect_ssh(
                hostname=hostname,
                username=username,
                password=password
            )
        else:
            # Get key path
            key_path = await cl.AskUserMessage(
                content="Enter path to private key file:",
                timeout=180
            ).send()
            
            if not key_path:
                await cl.Message(content="Connection cancelled - no key path provided").send()
                return
                
            # Try connecting without key password first
            result = await terminal_manager.terminal.connect_ssh(
                hostname=hostname,
                username=username,
                key_path=key_path
            )
            
            # If key is encrypted, ask for password
            if result.get('details', {}).get('error_type') == 'encrypted_key':
                key_password = await cl.AskUserMessage(
                    content="Key is encrypted. Please enter key password:",
                    timeout=180,
                    password=True
                ).send()
                
                if not key_password:
                    await cl.Message(content="Connection cancelled - no key password provided").send()
                    return
                    
                # Try again with key password
                result = await terminal_manager.terminal.connect_ssh(
                    hostname=hostname,
                    username=username,
                    key_path=key_path,
                    key_password=key_password
                )
        
        # Handle connection result
        if result['status'] == 'success':
            await cl.Message(content=f"✅ {result['message']}").send()
            return True
        else:
            await cl.Message(content=f"❌ Connection failed: {result['message']}").send()
            if 'error' in result.get('details', {}):
                await cl.Message(content=f"Error details: {result['details']['error']}").send()
            return False
            
    except Exception as e:
        await cl.Message(content=f"❌ Error during SSH connection: {str(e)}").send()
        return False

def parse_ssh_args(command: str) -> dict:
    """Parse SSH command line arguments into a dictionary."""
    args = command.split()
    params = {}
    i = 2  # Skip 'ssh connect'
    
    while i < len(args):
        if args[i] in ['-h', '--host']:
            if i + 1 < len(args):
                params['hostname'] = args[i + 1]
                i += 2
            else:
                raise ValueError("Missing hostname value after -h/--host")
        elif args[i] in ['-u', '--user']:
            if i + 1 < len(args):
                params['username'] = args[i + 1]
                i += 2
            else:
                raise ValueError("Missing username value after -u/--user")
        elif args[i] in ['-p', '--password']:
            if i + 1 < len(args):
                params['password'] = args[i + 1]
                i += 2
            else:
                raise ValueError("Missing password value after -p/--password")
        elif args[i] in ['-k', '--key']:
            if i + 1 < len(args):
                params['key_path'] = args[i + 1]
                i += 2
            else:
                raise ValueError("Missing key path value after -k/--key")
        else:
            i += 1
    
    return params

@cl.on_message
async def main(message: cl.Message):
    """Main message handler"""
    msg = message.content.strip()
    msg_lower = msg.lower()
    
    if msg_lower == "ssh help":
        help_text = terminal_manager.get_ssh_help()
        await cl.Message(content=help_text).send()
        return
        
    if msg_lower.startswith("ssh connect"):
        # Check if command line arguments are provided
        if len(msg.split()) > 2:
            try:
                # Parse command line arguments
                params = parse_ssh_args(msg)
                
                # If we have both hostname and username
                if 'hostname' in params and 'username' in params:
                    if 'password' in params:
                        # Connect with password
                        result = await terminal_manager.terminal.connect_ssh(
                            hostname=params['hostname'],
                            username=params['username'],
                            password=params['password']
                        )
                    elif 'key_path' in params:
                        # Connect with key
                        result = await terminal_manager.terminal.connect_ssh(
                            hostname=params['hostname'],
                            username=params['username'],
                            key_path=params['key_path']
                        )
                        
                        # If key is encrypted, fall back to interactive mode for key password
                        if result.get('details', {}).get('error_type') == 'encrypted_key':
                            await cl.Message(content="Key is encrypted, please provide the password.").send()
                            key_password = await cl.AskUserMessage(
                                content="Enter key password:",
                                timeout=180,
                                password=True
                            ).send()
                            
                            if key_password:
                                result = await terminal_manager.terminal.connect_ssh(
                                    hostname=params['hostname'],
                                    username=params['username'],
                                    key_path=params['key_path'],
                                    key_password=key_password
                                )
                    else:
                        # No authentication method provided, ask interactively
                        auth_method = await cl.AskUserMessage(
                            content="Choose authentication method (password/key):",
                            timeout=180
                        ).send()
                        
                        if auth_method and auth_method.lower() in ['password', 'key']:
                            if auth_method.lower() == 'password':
                                password = await cl.AskUserMessage(
                                    content="Enter password:",
                                    timeout=180,
                                    password=True
                                ).send()
                                if password:
                                    result = await terminal_manager.terminal.connect_ssh(
                                        hostname=params['hostname'],
                                        username=params['username'],
                                        password=password
                                    )
                            else:
                                key_path = await cl.AskUserMessage(
                                    content="Enter path to private key file:",
                                    timeout=180
                                ).send()
                                if key_path:
                                    result = await terminal_manager.terminal.connect_ssh(
                                        hostname=params['hostname'],
                                        username=params['username'],
                                        key_path=key_path
                                    )
                        else:
                            await cl.Message(content="Invalid authentication method").send()
                            return
                    
                    # Handle connection result
                    if result['status'] == 'success':
                        await cl.Message(content=f"✅ {result['message']}").send()
                    else:
                        await cl.Message(content=f"❌ Connection failed: {result['message']}").send()
                        if 'error' in result.get('details', {}):
                            await cl.Message(content=f"Error details: {result['details']['error']}").send()
                    return
                else:
                    # Missing required parameters, fall back to interactive mode
                    await handle_ssh_connection(message)
                    return
            except ValueError as e:
                await cl.Message(content=f"❌ Error parsing arguments: {str(e)}").send()
                return
            except Exception as e:
                await cl.Message(content=f"❌ Error during SSH connection: {str(e)}").send()
                return
        
        # No command line arguments provided, use interactive mode
        await handle_ssh_connection(message)
        return
    
    if msg == "ssh disconnect":
        result = terminal_manager.terminal.disconnect_ssh()
        await cl.Message(content=f"{'✅' if result['status'] == 'success' else '❌'} {result['message']}").send()
        return
    
    # Get current session state
    mode = cl.user_session.get('mode', 'chat')
    
    # Handle menu navigation
    if msg == "terminal":
        cl.user_session.set('mode', 'terminal')
        await create_terminal_interface()
        return
    
    # Handle terminal commands when in terminal mode
    if mode == 'terminal':
        if msg == 'exit':
            cl.user_session.set('mode', 'chat')
            await cl.Message(content="Exited terminal mode. Back to chat mode.").send()
            return
            
        if msg == 'clear':
            await create_terminal_interface()
            return
            
        # Execute command and update terminal
        result = await terminal_manager.execute_command(msg)
        terminal_manager.terminal.update_prompt()
        
        # Show command output with proper formatting
        if result.strip():
            await cl.Message(content=f"```terminal\n{result}\n```").send()
        
        # Show new prompt
        await cl.Message(content=f"```terminal\n{terminal_manager.terminal.prompt}```").send()
        return
    
    # Handle normal chat mode
    # Check if it's a direct terminal command (starts with !)
    if msg.startswith('!'):
        command = msg[1:].strip()
        result = await terminal_manager.execute_command(command)
        await update_terminal_display()
        await cl.Message(content=f"📝 Output:\n```\n{result}\n```").send()
        return
    
    # Special handling for command examples
    if msg.strip() in ['show command ls examples']:
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
                    "working_dir": terminal_manager.get_working_directory(cmd['command']),
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
        content=f"🤔 Processing your request: '{msg}'...\nThis may take a few moments."
    )
    await msg.send()
    
    try:
        # Process the request using the universal orchestrator
        response = await orchestrator.process_request(msg)
        
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