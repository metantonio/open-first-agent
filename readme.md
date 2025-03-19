# Multi-Agent System for Web Automation

This project implements multiple intelligent agent systems for web automation tasks, including cigar price comparison and DuckDuckGo search automation using OpenAI's GPT models and/or Open Source Models.

## Overview

The project consists of four main agent systems:
1. **Cigar Price Comparison Agent**: Scrapes, compares, and analyzes cigar prices from multiple online retailers
2. **Duck Browser Agent**: Automates DuckDuckGo searches and result processing
3. **Terraform Agent**: Manages and analyzes Infrastructure as Code configurations
4. **Development Environment Agent**: Automates setup of development environments and tools

## Project Structure

```
.
├── cigar_agents/                 # Cigar price comparison system
│   ├── __init__.py
│   ├── config.py                # Configuration for cigar agents
│   ├── orchestrator_agent.py    # Main orchestrator for cigar operations
│   ├── scraper_agent.py         # Website-specific scraping
│   ├── html_parser_agent.py     # Generic HTML parsing
│   └── export_agents.py         # Data export handling
│
├── duck_browser_agent/          # DuckDuckGo search system
│   ├── __init__.py
│   ├── config.py               # Configuration for duck browser agent
│   └── dds_agent.py            # DuckDuckGo search agent
│
├── terraform_agent/            # Infrastructure as Code system
│   ├── __init__.py
│   ├── config.py              # Configuration for terraform agents
│   ├── terraform_agent.py     # Main terraform agent implementation
│   └── terraform.tfvars       # Terraform variables
│
├── dev_env_agent/             # Development environment system
│   ├── __init__.py
│   ├── config.py             # Configuration for dev environment agents
│   └── dev_env_agent.py      # Development environment setup agents
│
├── aws_cli_agent/           # AWS CLI management system
│   ├── __init__.py
│   ├── config.py            # Configuration for AWS CLI agent
│   └── aws_cli_agent.py     # AWS CLI setup and configuration agent
│
├── tools/                     # Shared tools and utilities
│   └── __init__.py
│
├── universal_orchestrator.py  # Main orchestrator for all agent systems
├── ui.py                     # Chainlit UI for interactive usage
├── main.py                   # Main application entry point
├── config.py                 # Global configuration
├── requirements.txt          # Project dependencies
└── README.md                 # Project documentation
```

## Agent Systems

### 1. Cigar Price Comparison Agents

A multi-agent system that works together to compare cigar prices:

- **Orchestrator Agent**: Coordinates the workflow between specialized agents
- **Scraper Agent**: Handles website-specific scraping using CSS selectors
- **HTML Parser Agent**: Performs generic HTML parsing for product information
- **Export Agents**: Handle data export to JSON and CSV formats

### 2. Duck Browser Agent

An intelligent agent that interacts with DuckDuckGo search:

- **DDS Agent**: Performs automated searches and processes results
- **Chainlit UI**: Interactive web interface for the agent

### 3. Terraform Agents

A comprehensive multi-agent system for managing Infrastructure as Code with Terraform:

#### Main Agents

- **Terraform Orchestrator**: The main controller that coordinates all Terraform operations and other specialized agents
- **Terraform Editor**: Expert in creating and modifying Terraform configurations with best practices
- **Terraform Checker**: Validates configurations and provides detailed feedback

#### Specialized Analysis Agents

- **Security Analyzer**: Focuses on security configurations, IAM roles, and access controls
- **Cost Optimizer**: Analyzes and optimizes resource configurations for cost efficiency
- **Compliance Checker**: Ensures adherence to standards, naming conventions, and required settings
- **Performance Optimizer**: Analyzes and improves performance configurations
- **Structure Analyzer**: Reviews code organization, module structure, and best practices
- **Analysis Coordinator**: Coordinates the analysis process across specialized agents
- **Terraform Researcher**: Gathers and analyzes information from the web about Terraform best practices

### 4. Development Environment Agents

A specialized multi-agent system for setting up and configuring development environments:

#### Main Components

- **Development Environment Orchestrator**: Coordinates the entire setup process and manages interactions between specialized agents
- **IDE Setup Agent**: Expert in configuring VS Code and development tools
  - Configures VS Code for remote development
  - Sets up SSH configurations
  - Manages extensions and workspace settings
  - Handles Git integration
  - Configures debugging and user preferences

- **Environment Setup Agent**: Specialist in Python environment management
  - Creates and configures Conda environments
  - Sets up Jupyter integration
  - Manages package dependencies
  - Handles virtual environments
  - Configures environment variables

- **Jupyter Runner Agent**: Expert in managing Jupyter notebook execution
  - Starts and manages notebook servers
  - Creates new notebooks with templates
  - Configures notebook environments
  - Manages notebook directories
  - Handles server configuration
  - Provides access URLs and status

- **Notebook Monitor Agent**: Specialist in monitoring Jupyter notebook instances
  - Lists running notebook servers
  - Shows server URLs and directories
  - Monitors server status
  - Provides access information
  - Helps with server cleanup
  - Tracks notebook health

- **Help Agent**: Expert in explaining agent capabilities
  - Provides detailed information about all agents
  - Shows usage examples and workflows
  - Shares best practices
  - Guides users to appropriate tools
  - Answers capability questions

#### Key Features

- **VS Code Configuration**:
  - Remote SSH setup
  - Extension management
  - Workspace settings
  - Debugging configurations

- **Python Environment Management**:
  - Conda environment creation
  - Package installation
  - Dependency resolution
  - Virtual environment handling

- **Jupyter Integration**:
  - Kernel setup
  - Notebook configuration
  - Extension management
  - Server management
  - Notebook monitoring
  - Environment-specific kernels

### 5. AWS CLI Agent

A specialized agent system for managing AWS CLI installation, configuration, and testing:

#### Main Components

- **AWS CLI Configuration Agent**: Expert in AWS CLI setup and management
  - Checks AWS CLI installation status
  - Handles installation on different operating systems
  - Manages AWS credentials and configuration
  - Tests AWS connectivity
  - Ensures secure credential storage

#### Key Features

- **Installation Management**:
  - AWS CLI version detection
  - Operating system-specific installation
  - Installation verification
  - Version management

- **Configuration Management**:
  - AWS credentials setup
  - Region configuration
  - Output format settings
  - Multiple profile support
  - Secure credential storage

- **Security Features**:
  - Secure credential file permissions
  - Safe credential handling
  - Configuration backup
  - Best practices enforcement

#### Tools and Capabilities

- **Installation Tools**:
  - `check_aws_cli_installation`: Verifies AWS CLI installation and version
  - `install_aws_cli`: Handles OS-specific AWS CLI installation

- **Configuration Tools**:
  - `configure_aws_cli`: Sets up AWS credentials and configuration
  - `check_aws_configuration`: Validates current AWS setup
  - `test_aws_connection`: Tests AWS connectivity

The agent ensures:
- Proper AWS CLI installation and configuration
- Secure handling of AWS credentials
- Correct file permissions and storage
- Successful AWS connectivity
- Best practices implementation

Each agent has specific tools and capabilities:

- **IDE Setup Tools**:
  - `setup_vscode_remote`: Configures VS Code for remote SSH connections
  - `configure_vscode_extensions`: Installs and manages VS Code extensions

- **Environment Setup Tools**:
  - `setup_conda_env`: Creates and configures Conda environments
  - `setup_jupyter_kernel`: Sets up Jupyter kernels for environments

- **Jupyter Runner Tools**:
  - `start_jupyter_server`: Starts a Jupyter notebook server in a specific environment
  - `create_notebook`: Creates a new Jupyter notebook with basic setup
  - `list_running_notebooks`: Shows all running Jupyter notebook servers

- **Notebook Monitor Tools**:
  - `get_notebook_details`: Gets detailed information about running notebooks

- **Help Tools**:
  - `get_agent_capabilities`: Gets detailed information about all agents
  - `get_best_practices`: Gets development environment best practices

Each agent has specific responsibilities and tools:

- **Terraform Editor Tools**:
  - Create, read, and delete Terraform files
  - Run Terraform init and check commands
  - Validate configurations

- **Analysis Tools**:
  - Security analysis
  - Cost optimization
  - Compliance checking
  - Performance analysis
  - Code structure review
  - Web research for best practices

The agents work together to:
- Create and manage Terraform configurations
- Validate and check configurations before applying
- Analyze existing configurations for improvements
- Research and apply best practices
- Ensure security, compliance, and cost optimization

## Pre-requirements

If you are going to use Ollama, i recommend to download:
`qwen2.5-coder:7b` and `qwen2.5-coder:14b`

```bash
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:14b
```


## Installation

1. Clone the repository and create an environment:
```bash
git clone https://github.com/metantonio/open-first-agent
cd open-first-agent
conda create -n openai-first-agent python=3.10
conda activate openai-first-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key'
```

4. Disable agents tracing to OpenAI (optional)
```bash
export OPENAI_AGENTS_DISABLE_TRACING=1
```

## Running the Agents

### Running the Cigar Price Comparison Agent

1. Navigate to the project directory
2. Run the main script:
```bash
python main.py
```

The script will:
- Prompt for a cigar brand to search
- Scrape product information from supported websites
- Compare prices and find matching products
- Export results to JSON and CSV files
- Provide a summary of findings

### Running the Duck Browser Agent

1. Navigate to the project directory
2. Start the Chainlit UI:
```bash
chainlit run ui.py
```

This will:
- Launch a web interface at http://localhost:8000
- Allow you to interact with the DuckDuckGo search agent
- Process and display search results through the UI

## Features

- Multi-agent architecture for distributed tasks
- Web scraping with both selector-based and generic HTML parsing approaches
- Intelligent product matching across different websites
- Export functionality to both JSON and CSV formats
- Detailed logging and error handling
- Configurable model settings and parameters

## Configuration

The project uses a configuration system for both agent types that allows customization of:
- Model settings (temperature, max tokens, etc.)
- Export file paths and formats
- Logging levels and output locations
- Website-specific parameters

### API Key Requirements

The OpenAI API key has different requirements depending on your usage:

1. **Using OpenAI Models**:
   - A valid OpenAI API key with credits is **required**
   - The key is used for both model calls and trace logging
   - Set up the key as shown in the installation steps above

2. **Using Local LLMs (e.g., Ollama)**:
   - No OpenAI credits are required for model calls
   - A valid OpenAI API key is still required for trace logging
   - You can use a free API key with no credits
   - If you don't need tracing, you can skip the API key setup

### Model Configuration

Both agent systems use `config.py` files that allow you to configure which LLM provider to use. The system supports both local and cloud-based models:

1. **Using Local Models (Default)**
```python
# External LLM provider configuration (e.g., Ollama)
external_provider = {
    "model": "qwen2.5-coder:14b",
    "client": AsyncOpenAI(base_url="http://localhost:11434/v1")
}
```

2. **Using OpenAI Models**
```python
# OpenAI provider configuration
openai_provider = {
    "model": "gpt-4",
    "client": AsyncOpenAI()
}
```

Make sure to:
1. Have the appropriate API keys set up for your chosen provider
2. Install and configure Ollama if using local models
3. Set the OPENAI_API_KEY environment variable if using OpenAI models

## Development

To extend the project:
1. Add new agents in either the `cigar_agents` or `duck_browser_agent` directories
2. Implement new tools in the `tools` directory
3. Update the respective agent configurations
4. Maintain consistent error handling and logging

## Error Handling

The system implements comprehensive error handling:
- Graceful handling of website unavailability
- Validation of scraped data
- Logging of all operations and errors
- Fallback mechanisms for failed operations

## Logging

Each agent system maintains its own logs:

### Cigar Agents
- Logs are written to `cigar_scraper.log`
- Includes scraping operations, product matching details, and export operations

### Duck Browser Agent
- Logs are displayed in the Chainlit UI
- Includes search operations and result processing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT