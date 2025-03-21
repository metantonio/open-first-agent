import subprocess
import os
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from .config import get_model_config
import logging
from duckduckgo_search import DDGS
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re

model = get_model_config()
logger = logging.getLogger(__name__)
current_date = datetime.now().strftime("%Y-%m")

# Ensure output directory exists
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_working_directory() -> str:
    """Get the output directory path."""
    return OUTPUT_DIR

def get_terraform_file_path(filename: str) -> str:
    """Get the full path for a Terraform file in the output directory."""
    if not filename.endswith('.tf'):
        filename = f"{filename}.tf"
    return os.path.join(OUTPUT_DIR, filename)

# 1. Create Tools

@function_tool
def create_terraform_file(filename, content):
    """Create a new Terraform file with the specified content in the output directory."""
    try:
        filepath = get_terraform_file_path(filename)
        with open(filepath, 'w') as f:
            f.write(content)
        return f"Successfully created Terraform file: {filepath}"
    except Exception as e:
        return f"Error creating Terraform file: {str(e)}"

@function_tool
def delete_terraform_file(filename):
    """Delete a Terraform file from the output directory."""
    try:
        filepath = get_terraform_file_path(filename)
        os.remove(filepath)
        return f"Successfully deleted Terraform file: {filepath}"
    except Exception as e:
        return f"Error deleting Terraform file: {str(e)}"

@function_tool
def read_terraform_file(filename):
    """Read the contents of a Terraform file from the output directory."""
    try:
        filepath = get_terraform_file_path(filename)
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading Terraform file: {str(e)}"

@function_tool
def run_terraform_plan():
    """Execute 'terraform plan' command in the output directory."""
    try:
        result = subprocess.run(['terraform', 'plan'], 
                              capture_output=True, 
                              text=True,
                              cwd=OUTPUT_DIR)
        if result.returncode != 0:
            return f"Terraform plan failed:\n{result.stderr}"
        return f"Terraform plan output:\n{result.stdout}"
    except Exception as e:
        return f"Error running terraform plan: {str(e)}"

@function_tool
def run_terraform_apply():
    """Execute 'terraform apply' command with auto-approve in the output directory."""
    try:
        result = subprocess.run(['terraform', 'apply', '-auto-approve'], 
                              capture_output=True, 
                              text=True,
                              cwd=OUTPUT_DIR)
        if result.returncode != 0:
            return f"Terraform apply failed:\n{result.stderr}"
        return f"Terraform apply output:\n{result.stdout}"
    except Exception as e:
        return f"Error running terraform apply: {str(e)}"

@function_tool
def analyze_terraform_file(filename):
    """Analyze a Terraform file for best practices and potential improvements."""
    try:
        filepath = get_terraform_file_path(filename)
        example_path = os.path.join(os.path.dirname(__file__), 'terraform_example.tf')
        logger.info(f"Analyzing Terraform file: {example_path}")
        # Run terraform fmt to check formatting
        fmt_result = subprocess.run(['terraform', 'fmt', '-check', filepath],
                                  capture_output=True,
                                  text=True,
                                  cwd=OUTPUT_DIR)
        
        # Run terraform validate for syntax and configuration validation
        validate_result = subprocess.run(['terraform', 'validate'],
                                       capture_output=True,
                                       text=True,
                                       cwd=OUTPUT_DIR)
        
        # Read the file content for custom analysis
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Read the example file for comparison
        with open(example_path, 'r') as f:
            example_content = f.read()
            
        analysis_results = {
            'formatting': 'Properly formatted' if fmt_result.returncode == 0 else 'Needs formatting',
            'validation': validate_result.stdout if validate_result.returncode == 0 else validate_result.stderr,
            'content': content,
            'example': example_content
        }
        
        return analysis_results
    except Exception as e:
        return f"Error analyzing Terraform file: {str(e)}"

@function_tool
def search_terraform_info(topic):
    """Search for Terraform-related information using DuckDuckGo."""
    print(f"Searching for Terraform information about: {topic}")
    
    ddg_api = DDGS()
    results = ddg_api.text(f"terraform {topic} {current_date}", max_results=5)
    if results:
        search_results = "\n\n".join([f"Title: {result['title']}\nURL: {result['href']}\nDescription: {result['body']}" for result in results])
        return search_results
    else:
        return f"Could not find results for {topic}."

@function_tool
def fetch_and_parse_html(url):
    """Fetch HTML content from a URL and return only the body content."""
    logger.info(f"Fetching HTML content from {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()
            
        # Get body content
        body = soup.body
        if body is None:
            return "No body content found in the HTML"
            
        # Get text content
        text = body.get_text(separator='\n', strip=True)
        
        # Clean up excessive newlines and spaces
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

@function_tool
def run_terraform_check(filename=None):
    """Execute 'terraform check' command in the output directory."""
    try:
        # Change to output directory
        check_cmd = ['terraform', 'check']
        if filename:
            filepath = get_terraform_file_path(filename)
            check_cmd.append(filepath)
            
        result = subprocess.run(check_cmd,
                              capture_output=True,
                              text=True,
                              cwd=OUTPUT_DIR)
                              
        check_results = {
            'success': result.returncode == 0,
            'output': result.stdout if result.returncode == 0 else result.stderr,
            'file': filename if filename else 'all files'
        }
        
        return check_results
    except Exception as e:
        return f"Error running terraform check: {str(e)}"

@function_tool
def run_terraform_init():
    """Execute 'terraform init' command in the output directory."""
    try:
        result = subprocess.run(['terraform', 'init'],
                              capture_output=True,
                              text=True,
                              cwd=OUTPUT_DIR)
        if result.returncode != 0:
            return f"Terraform init failed:\n{result.stderr}"
        return f"Terraform init output:\n{result.stdout}"
    except Exception as e:
        return f"Error running terraform init: {str(e)}"

@function_tool
def manage_tfvars_file():
    """Check if terraform.tfvars exists in output directory, if not copy from example and return needed variables."""
    try:
        tfvars_path = os.path.join(OUTPUT_DIR, 'terraform.tfvars')
        example_path = os.path.join(os.path.dirname(__file__), 'terraform.tfvars.example')
        
        # Check if terraform.tfvars already exists
        if os.path.exists(tfvars_path):
            with open(tfvars_path, 'r') as f:
                current_content = f.read()
            
            # Parse current variables
            current_vars = {}
            for line in current_content.split('\n'):
                if '=' in line:
                    var_name = line.split('=')[0].strip()
                    var_value = line.split('=')[1].strip().strip('"')
                    current_vars[var_name] = var_value
                    
            return {
                'status': 'exists',
                'message': 'terraform.tfvars already exists and will not be modified',
                'current_variables': current_vars,
                'content': current_content,
                'file_path': tfvars_path
            }
        
        # Copy from example if it exists
        if os.path.exists(example_path):
            with open(example_path, 'r') as f:
                example_content = f.read()
            
            # Create new tfvars file
            with open(tfvars_path, 'w') as f:
                f.write(example_content)
            
            # Parse variables that need to be configured
            vars_needed = {}
            for line in example_content.split('\n'):
                if '=' in line:
                    var_name = line.split('=')[0].strip()
                    var_value = line.split('=')[1].strip().strip('"')
                    vars_needed[var_name] = var_value
            
            return {
                'status': 'created',
                'message': 'terraform.tfvars was created from example',
                'variables_needed': vars_needed,
                'file_path': tfvars_path
            }
        else:
            return {
                'status': 'error',
                'message': 'terraform.tfvars.example not found',
                'example_path': example_path
            }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error managing tfvars file: {str(e)}'
        }

@function_tool
def update_tfvars_file(variables):
    """Update terraform.tfvars with provided variable values."""
    try:
        tfvars_path = os.path.join(OUTPUT_DIR, 'terraform.tfvars')
        
        # Create content with new variables
        content = '\n'.join([f'{key} = "{value}"' for key, value in variables.items()])
        
        # Write to file
        with open(tfvars_path, 'w') as f:
            f.write(content)
            
        return {
            'status': 'success',
            'message': 'terraform.tfvars updated successfully'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error updating tfvars file: {str(e)}'
        }

@function_tool
def run_terminal_cmd(command, is_background=False, require_user_approval=True):
    """Execute a terminal command and return the output.
    
    Args:
        command (str): The command to execute
        is_background (bool): Whether to run the command in the background
        require_user_approval (bool): Whether to require user approval before execution
    """
    try:
        if is_background:
            # For background processes, use nohup and redirect output
            full_command = f"nohup {command} > /dev/null 2>&1 &"
        else:
            full_command = command
            
        result = subprocess.run(full_command, 
                              shell=True,
                              capture_output=True, 
                              text=True,
                              cwd=OUTPUT_DIR)
                              
        return {
            'success': result.returncode == 0,
            'output': result.stdout if result.returncode == 0 else result.stderr,
            'command': command,
            'is_background': is_background
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Error running terminal command: {str(e)}",
            'command': command,
            'is_background': is_background
        }

# 2. Create Single-Responsibility Agents

# Main File Management Agents
main_file_creator = Agent(
    name="Main File Creator",
    instructions="""You are responsible for ONLY creating and managing main.tf files.
    Your single responsibility is to:
    - Create main.tf with proper resource definitions
    - Ensure resource blocks are properly configured
    - Maintain resource dependencies in main.tf""",
    model=model,
    tools=[create_terraform_file, read_terraform_file, delete_terraform_file]
)

variables_file_creator = Agent(
    name="Variables File Creator",
    instructions="""You are responsible for ONLY creating and managing variables.tf files.
    Your single responsibility is to:
    - Create variables.tf with proper variable declarations
    - Ensure variable types and constraints are correct
    - Add meaningful variable descriptions""",
    model=model,
    tools=[create_terraform_file, read_terraform_file, delete_terraform_file]
)

outputs_file_creator = Agent(
    name="Outputs File Creator",
    instructions="""You are responsible for ONLY creating and managing outputs.tf files.
    Your single responsibility is to:
    - Create outputs.tf with proper output definitions
    - Ensure outputs reference valid resources
    - Add meaningful output descriptions""",
    model=model,
    tools=[create_terraform_file, read_terraform_file, delete_terraform_file]
)

provider_config_manager = Agent(
    name="Provider Config Manager",
    instructions="""You are responsible for ONLY managing provider configurations.
    Your single responsibility is to:
    - Configure provider blocks in main.tf
    - Ensure provider versions are specified
    - Set proper provider settings""",
    model=model,
    tools=[create_terraform_file, read_terraform_file, delete_terraform_file]
)

# Security Analysis Agents
security_group_analyzer = Agent(
    name="Security Group Analyzer",
    instructions="""You are responsible for ONLY analyzing security group configurations.
    Your single responsibility is to:
    - Review security group rules
    - Check for overly permissive rules
    - Validate ingress/egress settings""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

iam_analyzer = Agent(
    name="IAM Analyzer",
    instructions="""You are responsible for ONLY analyzing IAM configurations.
    Your single responsibility is to:
    - Review IAM roles and policies
    - Check for principle of least privilege
    - Validate IAM permissions""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

encryption_analyzer = Agent(
    name="Encryption Analyzer",
    instructions="""You are responsible for ONLY analyzing encryption settings.
    Your single responsibility is to:
    - Check for encryption at rest
    - Verify encryption in transit
    - Validate key management""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

network_security_analyzer = Agent(
    name="Network Security Analyzer",
    instructions="""You are responsible for ONLY analyzing network security.
    Your single responsibility is to:
    - Review network ACLs
    - Check VPC configurations
    - Validate network isolation""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

# Cost Analysis Agents
instance_cost_analyzer = Agent(
    name="Instance Cost Analyzer",
    instructions="""You are responsible for ONLY analyzing instance costs.
    Your single responsibility is to:
    - Review instance types and sizes
    - Check for cost-effective alternatives
    - Calculate instance costs""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

storage_cost_analyzer = Agent(
    name="Storage Cost Analyzer",
    instructions="""You are responsible for ONLY analyzing storage costs.
    Your single responsibility is to:
    - Review storage configurations
    - Check for cost-effective storage types
    - Calculate storage costs""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

network_cost_analyzer = Agent(
    name="Network Cost Analyzer",
    instructions="""You are responsible for ONLY analyzing network costs.
    Your single responsibility is to:
    - Review network configurations
    - Check for cost-effective networking
    - Calculate network costs""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

reserved_instance_analyzer = Agent(
    name="Reserved Instance Analyzer",
    instructions="""You are responsible for ONLY analyzing RI opportunities.
    Your single responsibility is to:
    - Identify RI candidates
    - Calculate potential savings
    - Recommend RI purchases""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

# Compliance Agents
tagging_compliance = Agent(
    name="Tagging Compliance",
    instructions="""You are responsible for ONLY checking tagging compliance.
    Your single responsibility is to:
    - Verify required tags
    - Check tag values
    - Ensure tag consistency""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

naming_compliance = Agent(
    name="Naming Compliance",
    instructions="""You are responsible for ONLY checking naming conventions.
    Your single responsibility is to:
    - Verify resource naming
    - Check variable naming
    - Ensure consistent naming""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

resource_compliance = Agent(
    name="Resource Compliance",
    instructions="""You are responsible for ONLY checking resource compliance.
    Your single responsibility is to:
    - Verify resource configurations
    - Check required settings
    - Validate resource properties""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

standards_compliance = Agent(
    name="Standards Compliance",
    instructions="""You are responsible for ONLY checking standards compliance.
    Your single responsibility is to:
    - Check against specific standards
    - Verify compliance requirements
    - Validate standard adherence""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

# Performance Agents
resource_size_optimizer = Agent(
    name="Resource Size Optimizer",
    instructions="""You are responsible for ONLY optimizing resource sizes.
    Your single responsibility is to:
    - Analyze resource utilization
    - Recommend optimal sizes
    - Calculate size impacts""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

network_performance = Agent(
    name="Network Performance",
    instructions="""You are responsible for ONLY analyzing network performance.
    Your single responsibility is to:
    - Review network configurations
    - Check bandwidth settings
    - Validate network optimization""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

storage_performance = Agent(
    name="Storage Performance",
    instructions="""You are responsible for ONLY analyzing storage performance.
    Your single responsibility is to:
    - Review storage configurations
    - Check IOPS settings
    - Validate storage optimization""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

scaling_optimizer = Agent(
    name="Scaling Optimizer",
    instructions="""You are responsible for ONLY analyzing scaling configurations.
    Your single responsibility is to:
    - Review auto-scaling settings
    - Check scaling policies
    - Validate scaling thresholds""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

# Structure Analysis Agents
file_structure_analyzer = Agent(
    name="File Structure Analyzer",
    instructions="""You are responsible for ONLY analyzing file organization.
    Your single responsibility is to:
    - Check file organization
    - Verify file naming
    - Validate file structure""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

module_analyzer = Agent(
    name="Module Analyzer",
    instructions="""You are responsible for ONLY analyzing module structure.
    Your single responsibility is to:
    - Review module organization
    - Check module interfaces
    - Validate module dependencies""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

dependency_analyzer = Agent(
    name="Dependency Analyzer",
    instructions="""You are responsible for ONLY analyzing resource dependencies.
    Your single responsibility is to:
    - Check resource dependencies
    - Verify dependency chains
    - Validate circular dependencies""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

code_style_analyzer = Agent(
    name="Code Style Analyzer",
    instructions="""You are responsible for ONLY analyzing code style.
    Your single responsibility is to:
    - Check code formatting
    - Verify style guidelines
    - Validate code consistency""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

# Research Agents
documentation_searcher = Agent(
    name="Documentation Searcher",
    instructions="""You are responsible for ONLY searching official documentation.
    Your single responsibility is to:
    - Search Terraform docs
    - Find relevant documentation
    - Extract official guidance""",
    model=model,
    tools=[search_terraform_info, fetch_and_parse_html]
)

community_practice_searcher = Agent(
    name="Community Practice Searcher",
    instructions="""You are responsible for ONLY searching community practices.
    Your single responsibility is to:
    - Search community forums
    - Find best practices
    - Extract community solutions""",
    model=model,
    tools=[search_terraform_info, fetch_and_parse_html]
)

version_compatibility_checker = Agent(
    name="Version Compatibility Checker",
    instructions="""You are responsible for ONLY checking version compatibility.
    Your single responsibility is to:
    - Check version requirements
    - Verify compatibility
    - Validate version constraints""",
    model=model,
    tools=[search_terraform_info, fetch_and_parse_html]
)

example_searcher = Agent(
    name="Example Searcher",
    instructions="""You are responsible for ONLY searching for examples.
    Your single responsibility is to:
    - Find code examples
    - Search reference implementations
    - Extract relevant patterns""",
    model=model,
    tools=[search_terraform_info, fetch_and_parse_html]
)

# Validation Agents
syntax_validator = Agent(
    name="Syntax Validator",
    instructions="""You are responsible for ONLY validating syntax.
    Your single responsibility is to:
    - Check HCL syntax
    - Verify block structure
    - Validate expression syntax""",
    model=model,
    tools=[read_terraform_file, run_terraform_check]
)

dependency_validator = Agent(
    name="Dependency Validator",
    instructions="""You are responsible for ONLY validating dependencies.
    Your single responsibility is to:
    - Check resource dependencies
    - Verify module dependencies
    - Validate provider dependencies""",
    model=model,
    tools=[read_terraform_file, run_terraform_check]
)

configuration_validator = Agent(
    name="Configuration Validator",
    instructions="""You are responsible for ONLY validating configurations.
    Your single responsibility is to:
    - Check resource configs
    - Verify provider configs
    - Validate variable configs""",
    model=model,
    tools=[read_terraform_file, run_terraform_check]
)

state_validator = Agent(
    name="State Validator",
    instructions="""You are responsible for ONLY validating state.
    Your single responsibility is to:
    - Check state consistency
    - Verify state locks
    - Validate state storage""",
    model=model,
    tools=[read_terraform_file, run_terraform_check]
)

# TFVars Agents
tfvars_reader = Agent(
    name="TFVars Reader",
    instructions="""You are responsible for ONLY reading tfvars files.
    Your single responsibility is to:
    - Read tfvars files
    - Parse variable values
    - Report current settings""",
    model=model,
    tools=[manage_tfvars_file]
)

tfvars_creator = Agent(
    name="TFVars Creator",
    instructions="""You are responsible for ONLY creating tfvars files.
    Your single responsibility is to:
    - Create new tfvars files
    - Set initial values
    - Handle file creation""",
    model=model,
    tools=[manage_tfvars_file]
)

tfvars_updater = Agent(
    name="TFVars Updater",
    instructions="""You are responsible for ONLY updating tfvars files.
    Your single responsibility is to:
    - Update variable values
    - Preserve existing values
    - Handle value changes""",
    model=model,
    tools=[update_tfvars_file]
)

tfvars_validator = Agent(
    name="TFVars Validator",
    instructions="""You are responsible for ONLY validating tfvars content.
    Your single responsibility is to:
    - Validate variable values
    - Check value types
    - Verify required values""",
    model=model,
    tools=[manage_tfvars_file]
)

# 3. Create Main Orchestrator Agent

orchestrator_agent = Agent(
    name="Terraform Orchestrator",
    instructions="""You are the main orchestrator for Terraform operations. Your responsibilities include:

    1. Initial Setup and Validation:
       - FIRST use tfvars_manager to check/setup terraform.tfvars
       - Wait for tfvars_manager to complete and return status
       - Based on tfvars_manager status, proceed with terraform_editor
       - Ensure proper sequence of operations
    
    2. Workflow Management:
       - Handle all transitions between agents
       - Maintain workflow state
       - Coordinate file operations
       - Ensure proper sequence of steps
    
    3. Variable Management:
       - Use tfvars_manager for all variable operations
       - Handle tfvars_manager responses appropriately
       - Coordinate variable updates when needed
       - Maintain variable state consistency
    
    4. File Creation Coordination:
       - After tfvars setup, use terraform_editor
       - Ensure all files are created in terraform directory
       - Maintain proper file organization
       - Handle file dependencies correctly
    
    5. Configuration Review:
       - Review file structure and organization
       - Check for basic syntax issues
       - Verify resource declarations
       - Ensure all required files are present
    
    6. Command Formatting:
       When showing commands to the user:
       - Format executable commands as:
         ```bash {{run}}
         command here
         ```
       - Format background commands as:
         ```bash {{run:background}}
         command here
         ```
       - Use ```bash for command examples
       - Always provide clear descriptions before each command
       - Example terraform commands:
         ```bash {{run}}
         terraform init
         ```
         ```bash {{run}}
         terraform plan
         ```
         ```bash {{run}}
         terraform apply
         ```
    
    7. Documentation and Guidance:
       - Provide clear documentation of created files
       - List available terraform commands with proper formatting
       - Guide user on manual execution steps
       - Include command descriptions and expected outcomes
    
    IMPORTANT: 
    - ALWAYS start with tfvars_manager for initial setup
    - Handle variable updates through tfvars_manager
    - Ensure all files are created in terraform directory
    - Follow security best practices
    - DO NOT automatically execute terraform commands
    - Follow this sequence:
      1. Use tfvars_manager for variables (setup or update)
      2. Wait for tfvars_manager completion
      3. Use terraform_editor for .tf files
      4. Review configuration
      5. Provide guidance with properly formatted commands""",
    tools=[
        create_terraform_file,
        delete_terraform_file,
        read_terraform_file,
        analyze_terraform_file,
        manage_tfvars_file,
        update_tfvars_file,
        run_terminal_cmd
    ],
    model=model,
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[
        main_file_creator,
        variables_file_creator,
        outputs_file_creator,
        provider_config_manager,
        security_group_analyzer,
        iam_analyzer,
        encryption_analyzer,
        network_security_analyzer,
        instance_cost_analyzer,
        storage_cost_analyzer,
        network_cost_analyzer,
        reserved_instance_analyzer,
        tagging_compliance,
        naming_compliance,
        resource_compliance,
        standards_compliance,
        resource_size_optimizer,
        network_performance,
        storage_performance,
        scaling_optimizer,
        file_structure_analyzer,
        module_analyzer,
        dependency_analyzer,
        code_style_analyzer,
        documentation_searcher,
        community_practice_searcher,
        version_compatibility_checker,
        example_searcher,
        syntax_validator,
        dependency_validator,
        configuration_validator,
        state_validator,
        tfvars_reader,
        tfvars_creator,
        tfvars_updater,
        tfvars_validator
    ]
)

# 4. Main workflow function

def run_workflow(request):
    """Run the Terraform workflow with the orchestrator as the main controller."""
    logger.info(f"Starting Terraform workflow for request: {request}")
    
    # First, handle tfvars setup with tfvars_manager
    tfvars_response = Runner.run_sync(
        tfvars_manager,
        f"""Check the status of terraform.tfvars and handle accordingly:
        1. Check if terraform.tfvars exists
        2. If it exists, read and report its content
        3. If it doesn't exist, create it from example
        4. Return clear status about the current state
        
        Request context: {request}"""
    )
    
    logger.info("TFVars Manager Response: %s", tfvars_response.final_output)
    
    # Then, proceed with terraform_editor regardless of tfvars status
    editor_response = Runner.run_sync(
        terraform_editor,
        f"""Create or modify Terraform configuration files based on this request: {request}
        
        Previous tfvars_manager response: {tfvars_response.final_output}
        
        Follow these steps:
        1. ALWAYS create/update main.tf with provider and resource configurations
        2. Create/update variables.tf for variable declarations
        3. Create/update outputs.tf if needed
        4. Ensure proper file structure and dependencies
        5. Format commands properly:
           ```bash {{run}}
           terraform init
           ```
        
        IMPORTANT:
        - Create all files in the output directory
        - main.tf MUST contain provider and resource blocks
        - Include necessary provider configurations
        - Add required resource definitions
        - Format any commands with proper {{run}} tags"""
    )
    
    logger.info("Terraform Editor Response: %s", editor_response.final_output)
    
    # Finally, use orchestrator to provide final response and guidance
    orchestrator_response = Runner.run_sync(
        orchestrator_agent,
        f"""Provide a final response for this request: {request}

        Context:
        - TFVars Status: {tfvars_response.final_output}
        - Editor Actions: {editor_response.final_output}

        Include in your response:
        1. Summary of what was done
        2. Current state of files
        3. Available commands with proper formatting:
           ```bash {{run}}
           terraform init
           ```
        4. Next steps for the user

        Remember to:
        - Format all commands properly with {{run}} tags
        - Provide clear guidance on next steps
        - Include all necessary terraform commands
        - Explain what each command does"""
    )
    
    # Combine all responses into a coherent output
    final_output = f"""
{tfvars_response.final_output}

{editor_response.final_output}

{orchestrator_response.final_output}
"""
    
    return final_output

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_request = "Create a basic AWS EC2 instance configuration"
    print(f"Running test with request: {test_request}")
    print(run_workflow(test_request)) 