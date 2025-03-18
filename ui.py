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
    # Check if it's a Terraform command
    if command.strip().startswith('terraform'):
        # Get the terraform working directory from environment or use default
        terraform_dir = os.getenv('TERRAFORM_WORKING_DIR', os.path.join(os.getcwd(), 'terraform'))
        # Create the directory if it doesn't exist
        os.makedirs(terraform_dir, exist_ok=True)
        return terraform_dir
    
    # For other commands, use the output directory by default
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

def process_code_blocks(content: str) -> tuple[str, list]:
    """Process content to find code blocks with run tags and create actions."""
    actions = []
    
    # Pattern to match code blocks with {run} or {run:background}
    pattern = r"```bash\s*{(run(?::background)?)}(.*?)```"
    
    def replacement(match):
        tag, code = match.groups()
        code = code.strip()
        is_background = tag == "run:background"
        
        # Create unique action ID
        action_id = f"run_{len(actions)}"
        
        # Determine working directory based on command
        working_dir = get_working_directory(code)
        
        # Add action for this code block
        actions.append(
            cl.Action(
                name=action_id,
                value=code,
                description=f"Run this command{' in background' if is_background else ''} (in {os.path.basename(working_dir)})",
                args={
                    "is_background": is_background,
                    "os": platform.system().lower(),
                    "working_dir": working_dir
                }
            )
        )
        
        # Return modified code block with button reference
        return f"```bash\n{code}\n```\n[Run Command in {os.path.basename(working_dir)}]($run_{len(actions)-1})"
    
    # Process all code blocks
    processed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    return processed_content, actions

@cl.on_message
async def main(message: cl.Message):
    """
    Main function to handle user messages and route them to appropriate agents.
    """
    # Get the user request
    request = message.content
    
    # Send a thinking message and show a loading indicator
    msg = cl.Message(
        content=f"🤔 Processing your request: '{request}'...\nThis may take a few moments.",
        author="AI Assistant"
    )
    await msg.send()
    
    try:
        # Process the request using the universal orchestrator
        response = await orchestrator.process_request(request)
        
        # Process the response for executable code blocks
        processed_content, actions = process_code_blocks(response)
        
        # Send response with actions
        msg = cl.Message(
            content=processed_content,
            author="AI Assistant"
        )
        
        if actions:
            msg.actions = actions
            
        await msg.send()
    except Exception as e:
        # Handle any errors
        error_message = f"❌ Sorry, I encountered an error: {str(e)}"
        if "429" in str(e):
            error_message += "\nIt seems we've hit an API rate limit. Please try again in a few minutes."
        await cl.Message(
            content=error_message,
            author="AI Assistant"
        ).send()

@cl.action_callback("run_")
async def on_action(action: cl.Action):
    """Handle execution of code blocks when action buttons are clicked."""
    command = action.value
    is_background = action.args.get("is_background", False)
    working_dir = action.args.get("working_dir")
    
    # Send a message indicating command execution
    await cl.Message(
        content=f"Executing command in {os.path.basename(working_dir)}:\n```bash\n{command}\n```",
        author="AI Assistant"
    ).send()
    
    # Execute the command
    result = await execute_command(command, is_background, working_dir)
    
    # Send the result
    await cl.Message(
        content=f"Command output:\n```\n{result}\n```",
        author="AI Assistant"
    ).send()

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


💡 Need help? Try these:
• "What can you help me with?"
• "Show me examples for [specific task]"
• "How do I [specific action]?"

Simply type your request, and I'll automatically determine the best way to help you!

What would you like to do?""",
        author="AI Assistant"
    ).send() 