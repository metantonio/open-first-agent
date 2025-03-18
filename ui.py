import chainlit as cl
from universal_orchestrator import orchestrator
import logging
import sys
import re
import asyncio
import subprocess
import platform
import os

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
    # Always use the output directory for all commands
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

async def execute_command(command: str, is_background: bool = False, working_dir: str = None) -> str:
    """Execute a shell command and return the output."""
    try:
        use_shell, shell_exe = get_shell_info()
        
        # Determine working directory
        cwd = working_dir if working_dir else get_working_directory(command)
        
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
            
            if process.returncode == 0:
                return f"Working directory: {cwd}\nOutput:\n{stdout.decode()}"
            else:
                return f"Error in directory {cwd}:\n{stderr.decode()}"
    except Exception as e:
        return f"Failed to execute command: {str(e)}"

def process_code_blocks(content: str) -> tuple[str, list[dict]]:
    """Process content to find code blocks with run tags and create Chainlit elements."""
    command_blocks = []
    
    # Pattern to match code blocks with {run} or {run:background}
    pattern = r"```bash\s*{(run(?::background)?)}(.*?)```"
    
    def create_command_block(code: str, is_background: bool) -> dict:
        """Create a command block with its associated elements."""
        code = code.strip()
        action_id = f"run_{len(command_blocks)}"
        working_dir = get_working_directory(code)
        
        return {
            'code': code,
            'is_background': is_background,
            'working_dir': working_dir,
            'action_id': action_id
        }
    
    def replacement(match):
        tag, code = match.groups()
        is_background = tag == "run:background"
        
        # Create command block
        command_block = create_command_block(code, is_background)
        command_blocks.append(command_block)
        
        # Return empty string as we'll handle the display separately
        return ""
    
    # Process all code blocks
    content_without_commands = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    return content_without_commands, command_blocks

@cl.on_message
async def main(message: cl.Message):
    """Main function to handle user messages and route them to appropriate agents."""
    request = message.content
    
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
                    description=f"Execute command in {os.path.basename(cmd_block['working_dir'])}",
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
        else:
            # If no commands, just send the content
            await cl.Message(content=response).send()
            
    except Exception as e:
        error_message = f"❌ Sorry, I encountered an error: {str(e)}"
        if "429" in str(e):
            error_message += "\nIt seems we've hit an API rate limit. Please try again in a few minutes."
        await cl.Message(content=error_message).send()

@cl.action_callback("run")
async def on_action(action: cl.Action):
    """Handle execution of code blocks when action buttons are clicked."""
    try:
        command = action.value
        payload = action.payload
        is_background = payload.get("is_background", False)
        working_dir = payload.get("working_dir")
        
        # Send execution message
        await cl.Message(
            content=f"💻 Executing: `{command}` in {os.path.basename(working_dir)}"
        ).send()
        
        # Execute the command
        result = await execute_command(command, is_background, working_dir)
        
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
    """
    Function that runs when a new chat session starts.
    """
    # Send a welcome message
    await cl.Message(
        content="""👋 Welcome to the AI Assistant!

I can help you with various tasks:

1. 🌐 Web Search and News:
   - Find and summarize news articles
   - Search for information on any topic
   - Process and analyze web content
   
   Examples:
   • "Search for recent developments in quantum computing"
   • "Find news about renewable energy technologies"

2. 🏗️ Terraform Infrastructure:
   - Create and manage Terraform configurations
   - Analyze security, cost, and performance
   - Execute Terraform operations
   - Validate infrastructure compliance
   - Optimize resource configurations
   - Research best practices
   
   Examples:
   • "Create a Terraform configuration for an AWS EC2 instance"
   • "Analyze the security of my Terraform configuration"
   • "Help me optimize my infrastructure costs"

3. 💻 Development Environment Setup:
   - Configure VS Code for remote development
   - Set up SSH connections and workspace settings
   - Install and manage VS Code extensions
   - Create and configure Conda environments
   - Set up Jupyter notebooks and kernels
   - Manage Python packages and dependencies
   
   Examples:
   • "Set up VS Code for remote development on my Linux server"
   • "Create a Conda environment for data science with Python 3.10"
   • "Configure Jupyter notebook in my ML environment"
   • "Start a Jupyter notebook server in the data-science environment"
   • "List all running notebooks"

4. ☁️ AWS CLI Configuration:
   - Check and install AWS CLI
   - Configure AWS credentials
   - Set up AWS SSO authentication
   - Manage AWS configuration files
   - Test AWS connectivity
   - Handle security best practices
   
   Examples:
   • "Check if AWS CLI is installed"
   • "Configure AWS CLI with SSO"
   • "Show me the required AWS CLI configuration format"
   • "Test my AWS connection"
   • "Set up AWS CLI with my credentials"

💡 Need help? Try these:
• "What can you help me with?"
• "Show me examples for [specific task]"
• "How do I [specific action]?"

Simply type your request, and I'll automatically determine the best way to help you!

What would you like to do?""",
        author="AI Assistant"
    ).send() 