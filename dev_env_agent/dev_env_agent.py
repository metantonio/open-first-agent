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
    handoffs=[ide_setup_agent, env_setup_agent, help_agent]
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