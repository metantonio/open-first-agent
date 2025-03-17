import subprocess
import os
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from .config import get_model_config
import logging
from datetime import datetime
import json
import webbrowser
from pathlib import Path
import sys
import time

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
    logger.info(f"Setting up Jupyter kernel for {env_name}")
    
    try:
        # First, ensure ipykernel is installed in the environment
        install_cmd = f"conda run -n {env_name} pip install ipykernel"
        logger.info("Installing ipykernel...")
        subprocess.run(install_cmd.split(), check=True)
        
        # Get the platform-specific user directory for kernel specs
        if sys.platform == "darwin":  # macOS
            kernel_dir = os.path.expanduser("~/Library/Jupyter/kernels")
        elif sys.platform == "linux":  # Linux
            kernel_dir = os.path.expanduser("~/.local/share/jupyter/kernels")
        else:  # Windows or others
            kernel_dir = os.path.expanduser("~/.jupyter/kernels")
        
        # Ensure the kernel directory exists
        os.makedirs(kernel_dir, exist_ok=True)
        
        # Install the kernel using a list of arguments to avoid shell parsing issues
        cmd = [
            "conda", "run", "-n", env_name, 
            "python", "-m", "ipykernel", "install",
            "--user",
            "--name", env_name,
            "--display-name", f"Python ({env_name})"
        ]
        
        logger.info(f"Installing kernel with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = result.stderr or "Unknown error occurred"
            logger.error(f"Failed to install kernel: {error_msg}")
            
            # Try alternative installation method if the first one fails
            logger.info("Attempting alternative kernel installation method...")
            alt_cmd = [
                "conda", "run", "-n", env_name,
                "ipython", "kernel", "install",
                "--user",
                "--name", env_name,
                "--display-name", f"Python ({env_name})"
            ]
            
            try:
                alt_result = subprocess.run(alt_cmd, capture_output=True, text=True)
                if alt_result.returncode == 0:
                    logger.info("Alternative kernel installation succeeded")
                else:
                    logger.error(f"Alternative installation failed: {alt_result.stderr}")
                    return f"Error installing Jupyter kernel: {error_msg}"
            except Exception as e:
                logger.error(f"Alternative installation failed with error: {str(e)}")
                return f"Error installing Jupyter kernel: {error_msg}"
        
        # Verify the kernel installation
        kernel_path = os.path.join(kernel_dir, env_name)
        if os.path.exists(kernel_path):
            logger.info(f"Successfully installed kernel at {kernel_path}")
            return f"Successfully installed Jupyter kernel for {env_name}"
        
        # If kernel_path doesn't exist, check for json file
        json_path = os.path.join(kernel_dir, f"{env_name}/kernel.json")
        if os.path.exists(json_path):
            logger.info(f"Successfully installed kernel (found kernel.json at {json_path})")
            return f"Successfully installed Jupyter kernel for {env_name}"
            
        logger.warning(f"Kernel directory not found at {kernel_path}")
        return f"Kernel installation completed but kernel directory not found. You may need to restart Jupyter."
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
        logger.error(f"Error during kernel setup: {error_msg}")
        return f"Failed to set up Jupyter kernel: {error_msg}"
    except Exception as e:
        logger.error(f"Unexpected error during kernel setup: {str(e)}")
        return f"Unexpected error during kernel setup: {str(e)}"

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

# Add Jupyter Runner Tools and Agent
@function_tool
def start_jupyter_server(env_name, notebook_dir=None):
    """Start a Jupyter notebook server in the specified environment."""
    try:
        # First verify the conda environment exists
        try:
            env_check = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
            if env_name not in env_check.stdout:
                return f"Error: Conda environment '{env_name}' does not exist. Please create it first."
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking conda environments: {str(e)}")
            return "Error: Could not verify conda environments. Please check if conda is installed and working."

        # Check if Jupyter is already installed in the environment without trying to run it
        check_jupyter_cmd = ["conda", "run", "-n", env_name, "pip", "list"]
        jupyter_check = subprocess.run(check_jupyter_cmd, capture_output=True, text=True)
        needs_jupyter = "jupyter" not in jupyter_check.stdout.lower()
        
        if needs_jupyter:
            logger.info("Jupyter not found in environment, installing...")
            install_cmd = f"conda run -n {env_name} pip install jupyter notebook"
            try:
                subprocess.run(install_cmd.split(), check=True)
                logger.info("Successfully installed Jupyter")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install Jupyter: {str(e)}")
                return f"Error: Failed to install Jupyter in environment {env_name}"
        else:
            logger.info("Jupyter already installed in environment")

        # List of potential directories to try, in order of preference
        potential_dirs = [
            notebook_dir if notebook_dir else None,  # User specified directory (if any)
            os.path.expanduser("~/jupyter_notebooks"),  # Home directory
            os.path.expanduser("~/Documents/jupyter_notebooks"),  # Documents folder
            os.path.join(os.path.expanduser("~"), "Desktop", "jupyter_notebooks"),  # Desktop
            os.path.join("/tmp", f"jupyter_{env_name}"),  # Temporary directory
        ]
        
        # Remove None entries
        potential_dirs = [d for d in potential_dirs if d is not None]
        
        # Try each directory until we find one that works
        notebook_dir = None
        for dir_path in potential_dirs:
            try:
                # Convert to absolute path and resolve any symlinks
                test_dir = os.path.abspath(os.path.expanduser(dir_path))
                
                # Try to create a test file to verify write permissions
                test_file = os.path.join(test_dir, '.write_test')
                os.makedirs(test_dir, mode=0o755, exist_ok=True)
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                
                # If we get here, the directory is writable
                notebook_dir = test_dir
                logger.info(f"Successfully found writable directory: {notebook_dir}")
                break
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not use directory {dir_path}: {str(e)}")
                continue
        
        if notebook_dir is None:
            raise PermissionError("Could not find any writable directory for Jupyter notebooks")
        
        # Check if a Jupyter server is already running
        try:
            result = subprocess.run(['jupyter', 'notebook', 'list'], 
                                  capture_output=True, 
                                  text=True)
            if "http://localhost:8888" in result.stdout:
                logger.info("Jupyter server already running")
                return "Jupyter server is already running. Check 'jupyter notebook list' for details."
        except Exception:
            pass
        
        if sys.platform == "darwin":  # macOS
            # Create a temporary shell script to run Jupyter
            script_dir = os.path.dirname(notebook_dir)  # Use parent directory for script
            script_path = os.path.join(script_dir, "start_jupyter.command")
            
            # Prepare the Jupyter command with explicit port and no-browser option
            jupyter_cmd = f"conda run -n {env_name} jupyter notebook --notebook-dir='{notebook_dir}' --port=8888 --no-browser"
            
            try:
                with open(script_path, "w") as f:
                    f.write("#!/bin/bash\n")
                    f.write(f"cd '{notebook_dir}'\n")
                    f.write(jupyter_cmd + "\n")
                
                # Make the script executable
                os.chmod(script_path, 0o755)
                
                # Open the script in a new terminal window
                subprocess.Popen(["open", script_path])
                
                # Wait for server to start
                max_attempts = 6
                for attempt in range(max_attempts):
                    time.sleep(5)  # Wait 5 seconds between checks
                    try:
                        result = subprocess.run(['jupyter', 'notebook', 'list'], 
                                              capture_output=True, 
                                              text=True)
                        if "http://localhost:8888" in result.stdout:
                            url = "http://localhost:8888"
                            try:
                                webbrowser.open(url)
                            except Exception as e:
                                logger.warning(f"Could not open browser: {str(e)}")
                            
                            return f"""Jupyter server started successfully!
                            Directory: {notebook_dir}
                            Access URL: {url}
                            
                            The server is running in a new terminal window.
                            To stop the server, close the terminal window or press Ctrl+C in that window."""
                    except Exception:
                        continue
                
                return f"""Started Jupyter server in a new terminal window.
                Directory: {notebook_dir}
                
                Please wait a moment and check the terminal window for the URL.
                To stop the server, close the terminal window or press Ctrl+C in that window."""
                
            except Exception as e:
                logger.error(f"Error creating startup script: {str(e)}")
                # Fall through to non-macOS method if script creation fails
        
        # For non-macOS platforms or if macOS script method fails
        # Prepare the command with explicit port
        jupyter_cmd = f"conda run -n {env_name} jupyter notebook --notebook-dir='{notebook_dir}' --port=8888"
        
        return f"""To start Jupyter, open a new terminal and run:
        {jupyter_cmd}
        
        Or run this in your current terminal:
        {jupyter_cmd} &
        
        The notebook directory will be: {notebook_dir}"""
            
    except Exception as e:
        error_msg = f"Error starting Jupyter server: {str(e)}"
        logger.error(error_msg)
        return f"{error_msg}\n\nPlease try running Jupyter directly in a new terminal with:\nconda run -n {env_name} jupyter notebook"

@function_tool
def create_notebook(env_name, notebook_name, notebook_dir=None):
    """Create a new Jupyter notebook with basic setup."""
    if notebook_dir is None:
        notebook_dir = os.getcwd()
    
    # Ensure the directory exists
    os.makedirs(notebook_dir, exist_ok=True)
    
    # Full path for the notebook
    notebook_path = os.path.join(notebook_dir, f"{notebook_name}.ipynb")
    
    # Basic notebook structure with Python 3 kernel
    notebook_content = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# " + notebook_name + "\n", "Created on: " + datetime.now().strftime("%Y-%m-%d")]
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": ["# Import common libraries\nimport numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt"],
                "outputs": [],
                "execution_count": None
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": env_name,
                "language": "python",
                "name": env_name
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    # Write the notebook
    with open(notebook_path, 'w') as f:
        json.dump(notebook_content, f, indent=2)
    
    return f"Created notebook: {notebook_path}"

@function_tool
def list_running_notebooks():
    """List all running Jupyter notebook servers."""
    cmd = "jupyter notebook list"
    result = subprocess.run(cmd.split(), capture_output=True, text=True)
    return result.stdout

jupyter_runner_agent = Agent(
    name="Jupyter Runner Agent",
    instructions="""You are a Jupyter notebook execution expert. Your responsibilities include:
    
    1. Manage Jupyter servers:
       - Start notebook servers
       - Monitor running instances
       - Handle server configuration
       - Manage notebook directories
       - Tell the user that the server is running and provide the URL http://localhost:8888
    
    2. Create and organize notebooks:
       - Create new notebooks
       - Set up basic templates
       - Configure kernels
       - Organize notebook structure
    
    3. Handle notebook execution:
       - Start notebooks in correct environments
       - Monitor notebook status
       - Manage running instances
       - Provide access URLs
    
    4. Manage notebook workflow:
       - Create proper directory structure
       - Set up working directories
       - Handle notebook dependencies
       - Ensure proper kernel selection
    
    Focus on providing a smooth notebook execution experience.""",
    model=model,
    tools=[start_jupyter_server, create_notebook, list_running_notebooks]
)

# Add Help Agent
@function_tool
def get_agent_capabilities():
    """Get detailed information about agent capabilities and examples."""
    capabilities = {
        "IDE Setup Agent": {
            "description": "Configures VS Code and development tools",
            "capabilities": [
                "Remote SSH setup",
                "Extension management",
                "Workspace configuration",
                "Git integration",
                "Debugging setup"
            ],
            "tools": [
                "setup_vscode_remote: Configure VS Code for remote SSH connections",
                "configure_vscode_extensions: Install and manage VS Code extensions"
            ],
            "examples": [
                "Set up VS Code for remote development on my Linux server at 192.168.1.100",
                "Install Python and Jupyter extensions in VS Code",
                "Configure VS Code for Python debugging",
                "Set up Git integration in VS Code",
                "Configure my workspace settings for Python development"
            ]
        },
        "Environment Setup Agent": {
            "description": "Manages Python environments and tools",
            "capabilities": [
                "Conda environment creation",
                "Package management",
                "Jupyter integration",
                "Virtual environment handling",
                "Dependency resolution"
            ],
            "tools": [
                "setup_conda_env: Create and configure Conda environments with specific Python versions and packages",
                "setup_jupyter_kernel: Set up Jupyter kernels for Conda environments"
            ],
            "examples": [
                "Create a new Conda environment for data science with Python 3.10",
                "Set up Jupyter notebook in my data-science environment",
                "Install TensorFlow and PyTorch in my ML environment",
                "Create a Python environment with specific package versions",
                "Set up a development environment for web development"
            ]
        },
        "Jupyter Runner Agent": {
            "description": "Manages and runs Jupyter notebooks",
            "capabilities": [
                "Start Jupyter servers",
                "Create new notebooks",
                "Monitor running instances",
                "Manage notebook directories",
                "Configure notebook environments"
            ],
            "tools": [
                "start_jupyter_server: Start a Jupyter notebook server in a specific environment",
                "create_notebook: Create a new Jupyter notebook with basic setup",
                "list_running_notebooks: Show all running Jupyter notebook servers"
            ],
            "examples": [
                "Start a Jupyter server in my data-science environment",
                "Create a new notebook for my machine learning project",
                "Show me all running Jupyter servers",
                "Set up a new data analysis notebook in the projects directory",
                "Start Jupyter in my ML environment with TensorFlow"
            ]
        },
        "Help Agent": {
            "description": "Provides guidance and information about the development environment system",
            "capabilities": [
                "Explain agent capabilities",
                "Provide usage examples",
                "Answer capability questions",
                "Suggest best practices",
                "Guide users to appropriate agents"
            ],
            "tools": [
                "get_agent_capabilities: Get detailed information about all agents and their capabilities"
            ],
            "examples": [
                "What can the IDE Setup Agent do?",
                "Show me examples of environment setup",
                "How do I set up a remote development environment?",
                "What are the best practices for Python development?",
                "Which agent should I use for Jupyter setup?"
            ]
        }
    }
    return capabilities

@function_tool
def get_best_practices():
    """Get development environment best practices and recommendations."""
    best_practices = {
        "VS Code Setup": [
            "Always use version control extensions",
            "Configure autosave and formatting",
            "Set up consistent indentation",
            "Use integrated terminal",
            "Enable multi-root workspaces for complex projects"
        ],
        "Python Environment": [
            "Use virtual environments for each project",
            "Maintain requirements.txt or environment.yml",
            "Pin dependency versions",
            "Use .env files for environment variables",
            "Regular environment cleanup"
        ],
        "Remote Development": [
            "Use SSH keys instead of passwords",
            "Configure proper file synchronization",
            "Set up local backup of configurations",
            "Use workspace-specific settings",
            "Enable port forwarding when needed"
        ],
        "Jupyter Integration": [
            "Use environment-specific kernels",
            "Enable notebook extensions",
            "Regular checkpoint saves",
            "Use clear notebook naming conventions",
            "Separate code and data directories"
        ],
        "Jupyter Workflow": [
            "Use clear notebook naming conventions",
            "Organize notebooks in project-specific directories",
            "Regular notebook checkpoints",
            "Clear cell output before sharing",
            "Use markdown for documentation",
            "Keep code cells focused and modular",
            "Use environment-specific kernels",
            "Version control your notebooks"
        ]
    }
    return best_practices

# Update Help Agent with tools
help_agent = Agent(
    name="Help Agent",
    instructions="""You are an expert in explaining the capabilities of all development environment agents. Your responsibilities include:
    
    1. Explain agent capabilities:
       - Use get_agent_capabilities to obtain detailed information
       - Describe what each agent can do
       - List available tools and their purposes
       - Provide specific examples
       - Suggest common use cases
    
    2. Provide usage examples:
       - Show example commands
       - Demonstrate typical workflows
       - Explain expected outcomes
       - Include real-world scenarios
    
    3. Share best practices:
       - Use get_best_practices to provide recommendations
       - Suggest optimal configurations
       - Guide on tool selection
       - Advise on common pitfalls
    
    4. Answer capability questions:
       - Clarify agent limitations
       - Explain tool interactions
       - Guide users to appropriate agents
       - Provide context-specific advice
    
    Focus on making the system easy to understand and use. Always provide specific, actionable information based on the tools' output.""",
    model=model,
    tools=[get_agent_capabilities, get_best_practices]
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
       - Notebook execution
    
    3. Handle user preferences:
       - Custom configurations
       - Tool preferences
       - Workflow optimization
    
    4. Provide help and guidance:
       - Explain available capabilities
       - Show relevant examples
       - Guide users to appropriate tools
    
    Ensure a smooth and consistent setup process.""",
    model=model,
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[ide_setup_agent, env_setup_agent, jupyter_runner_agent, help_agent]
)

# 4. Main workflow function

def run_workflow(request):
    """Run the development environment setup workflow."""
    logger.info(f"Starting development environment setup for request: {request}")
    
    orchestrator_response = Runner.run_sync(
        orchestrator_agent,
        f"""Process this development environment setup request: {request}

        1. If this is a help request or contains '?', use the help agent to:
           - Explain relevant capabilities
           - Provide specific examples
           - Suggest next steps

        2. For setup requests:
           - Analyze the requirements
           - Set up IDE configurations
           - Create and configure Python environment
           - Set up Jupyter integration if needed
           - Validate the setup

        IMPORTANT: 
        - Ensure all tools are properly configured
        - Handle errors gracefully
        - Provide clear feedback
        - Document the setup process
        - For help requests, be thorough in explanations

        Handle all steps appropriately and provide detailed feedback.
        """
    )
    
    return orchestrator_response.final_output

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_request = "Set up a Python data science environment with VS Code and Jupyter"
    print(f"Running test with request: {test_request}")
    print(run_workflow(test_request)) 