import subprocess
import os
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from .config import get_model_config
import logging
from datetime import datetime
import json

model = get_model_config()
logger = logging.getLogger(__name__)

# Ensure output directory exists
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Create Tools

@function_tool
def setup_vscode_remote(host, user, key_path):
    """Configure VS Code for remote SSH connection."""
    config_dir = os.path.expanduser("~/.ssh/")
    config_file = os.path.join(config_dir, "config")
    
    # Ensure .ssh directory exists
    os.makedirs(config_dir, exist_ok=True)
    
    # Add SSH config
    config_entry = f"""
Host {host}
    HostName {host}
    User {user}
    IdentityFile {key_path}
    """
    
    with open(config_file, "a") as f:
        f.write(config_entry)
    
    return f"Added SSH configuration for {host}"

@function_tool
def setup_conda_env(env_name, python_version, packages=None):
    """Create and configure a Conda environment."""
    if packages is None:
        packages = []
    
    # Create environment
    create_cmd = f"conda create -n {env_name} python={python_version} -y"
    subprocess.run(create_cmd.split(), check=True)
    
    # Install packages if specified
    if packages:
        install_cmd = f"conda run -n {env_name} pip install {' '.join(packages)}"
        subprocess.run(install_cmd.split(), check=True)
    
    return f"Created Conda environment {env_name} with Python {python_version}"

@function_tool
def setup_jupyter_kernel(env_name):
    """Set up Jupyter kernel for Conda environment."""
    cmd = f"conda run -n {env_name} python -m ipykernel install --user --name {env_name}"
    subprocess.run(cmd.split(), check=True)
    return f"Installed Jupyter kernel for {env_name}"

@function_tool
def configure_vscode_extensions(extensions=None):
    """Install and configure VS Code extensions."""
    if extensions is None:
        extensions = [
            "ms-python.python",
            "ms-toolsai.jupyter",
            "ms-vscode-remote.remote-ssh"
        ]
    
    for ext in extensions:
        cmd = f"code --install-extension {ext}"
        subprocess.run(cmd.split(), check=True)
    
    return f"Installed VS Code extensions: {', '.join(extensions)}"

# 2. Create Specialized Agents

ide_setup_agent = Agent(
    name="IDE Setup Agent",
    instructions="""You are an IDE configuration expert. Your responsibilities include:
    
    1. Configure VS Code for remote development:
       - Set up SSH configurations
       - Configure remote extensions
       - Set up workspace settings
    
    2. Install and configure extensions:
       - Python extension
       - Jupyter extension
       - Remote development extensions
       - Git integration
    
    3. Set up user preferences:
       - Editor settings
       - Theme and appearance
       - Keyboard shortcuts
       - Debugging configurations
    
    Focus on creating a smooth development experience.""",
    model=model,
    tools=[setup_vscode_remote, configure_vscode_extensions]
)

env_setup_agent = Agent(
    name="Environment Setup Agent",
    instructions="""You are a Python environment setup expert. Your responsibilities include:
    
    1. Set up Conda environments:
       - Create new environments
       - Install required packages
       - Configure environment variables
    
    2. Configure Jupyter integration:
       - Install Jupyter kernels
       - Set up notebook configurations
       - Configure extensions
    
    3. Manage dependencies:
       - Handle package conflicts
       - Update requirements files
       - Manage virtual environments
    
    Focus on creating stable and reproducible environments.""",
    model=model,
    tools=[setup_conda_env, setup_jupyter_kernel]
)

# 3. Create Main Orchestrator

orchestrator_agent = Agent(
    name="Development Environment Orchestrator",
    instructions="""You are the main orchestrator for setting up development environments. Your responsibilities include:
    
    1. Coordinate environment setup:
       - Determine required components
       - Sequence setup steps
       - Validate configurations
    
    2. Manage tool integration:
       - IDE setup
       - Environment management
       - Jupyter configuration
    
    3. Handle user preferences:
       - Custom configurations
       - Tool preferences
       - Workflow optimization
    
    Ensure a smooth and consistent setup process.""",
    model=model,
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[ide_setup_agent, env_setup_agent]
)

# 4. Main workflow function

def run_workflow(request):
    """Run the development environment setup workflow."""
    logger.info(f"Starting development environment setup for request: {request}")
    
    orchestrator_response = Runner.run_sync(
        orchestrator_agent,
        f"""Process this development environment setup request: {request}

        1. Analyze the requirements
        2. Set up IDE configurations
        3. Create and configure Python environment
        4. Set up Jupyter integration if needed
        5. Validate the setup

        IMPORTANT: 
        - Ensure all tools are properly configured
        - Handle errors gracefully
        - Provide clear feedback
        - Document the setup process

        Handle all steps appropriately and provide detailed feedback.
        """
    )
    
    return orchestrator_response.final_output

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_request = "Set up a Python data science environment with VS Code and Jupyter"
    print(f"Running test with request: {test_request}")
    print(run_workflow(test_request)) 