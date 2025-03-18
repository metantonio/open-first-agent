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

# 2. Create Editor Agent for Terraform

terraform_editor = Agent(
    name="Terraform Editor",
    instructions="""You are a Terraform configuration expert. Your responsibilities include:
    1. Create and manage Terraform configuration files:
       - Create new .tf files in the output directory
       - Ensure files follow proper naming conventions
       - Maintain file organization and structure
    
    2. Implement Terraform best practices:
       - Follow HashiCorp style guidelines
       - Use proper resource naming
       - Add appropriate tags and descriptions
       - Include necessary comments
    
    3. Handle configuration components:
       - Configure provider blocks correctly
       - Define resource configurations
       - Set up data sources
       - Create output definitions
    
    4. Manage variable declarations:
       - Create variables.tf for variable definitions
       - Define proper variable types and constraints
       - Add meaningful variable descriptions
       - Set default values when appropriate
    
    When creating or modifying files:
    1. ALWAYS create files in the output directory
    2. Start with provider and backend configurations
    3. Include all necessary resource definitions
    4. Add required variable declarations
    
    IMPORTANT:
    - All files must be created in the output directory
    - Coordinate with tfvars_manager for variable values
    - Ensure all dependencies are properly declared
    - Follow security best practices
    - DO NOT execute terraform commands (init/plan/apply)
    - Only create and manage .tf files
    
    When showing commands:
    - Format executable commands as ```bash {{run}}
    command here
    ```
    - Format background commands as ```bash {{run:background}}
    command here
    ```
    - Use ```bash for command examples
    - Provide clear description before each command""",
    model=model,
    tools=[
        create_terraform_file,
        read_terraform_file,
        delete_terraform_file,
        run_terminal_cmd
    ]
)

# 2.1 Create Specialized Analysis Agents

security_analyzer = Agent(
    name="Security Analyzer",
    instructions="""You are a Terraform security analysis expert. Your responsibilities include:
    
    1. Analyze security configurations:
       - Review security group rules and restrictions
       - Check for encryption settings
       - Verify IAM roles and permissions
       - Validate network access controls
       - Check for secure protocols and settings
    
    2. Compare with security best practices:
       - Identify missing security measures
       - Check for overly permissive access
       - Verify secure defaults
       - Validate authentication methods
    
    3. Provide security recommendations:
       - Suggest security improvements
       - Identify potential vulnerabilities
       - Recommend access restrictions
       - Propose encryption enhancements
    
    Focus on security aspects and provide clear, actionable security recommendations.""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

cost_optimizer = Agent(
    name="Cost Optimizer",
    instructions="""You are a Terraform cost optimization expert. Your responsibilities include:
    
    1. Analyze resource configurations for cost:
       - Instance types and sizes
       - Storage configurations
       - Network resources
       - Service selections
    
    2. Identify cost-saving opportunities:
       - Resource right-sizing
       - Reserved instances potential
       - Storage optimizations
       - Network cost reductions
    
    3. Provide cost optimization recommendations:
       - Specific cost-saving measures
       - ROI calculations
       - Implementation priorities
       - Alternative configurations
    
    Focus on cost aspects and provide clear, actionable cost-saving recommendations.""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

compliance_checker = Agent(
    name="Compliance Checker",
    instructions="""You are a Terraform compliance expert. Your responsibilities include:
    
    1. Check compliance with standards:
       - Tagging requirements
       - Naming conventions
       - Resource configurations
       - Required settings
    
    2. Validate against example patterns:
       - Compare with reference architecture
       - Check for required components
       - Verify configuration patterns
       - Validate structure
    
    3. Provide compliance recommendations:
       - Required changes for compliance
       - Best practices alignment
       - Documentation requirements
       - Standardization suggestions
    
    Focus on compliance and standardization aspects.""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

performance_optimizer = Agent(
    name="Performance Optimizer",
    instructions="""You are a Terraform performance optimization expert. Your responsibilities include:
    
    1. Analyze performance configurations:
       - Resource sizing
       - Network settings
       - Storage performance
       - Service configurations
    
    2. Identify performance improvements:
       - Resource optimizations
       - Configuration enhancements
       - Architecture improvements
       - Scaling recommendations
    
    3. Provide performance recommendations:
       - Specific performance improvements
       - Configuration changes
       - Architecture updates
       - Scaling strategies
    
    Focus on performance aspects and provide clear, actionable recommendations.""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

structure_analyzer = Agent(
    name="Structure Analyzer",
    instructions="""You are a Terraform code structure expert. Your responsibilities include:
    
    1. Analyze code organization:
       - File structure
       - Module organization
       - Variable management
       - Resource grouping
    
    2. Check structural elements:
       - Provider configurations
       - Backend settings
       - Variable declarations
       - Output definitions
       - Formatting
    
    3. Provide structural recommendations:
       - Code organization improvements
       - Module structuring
       - File organization
       - Best practices implementation
    
    Focus on code structure and organization aspects.""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

# 2.2 Create Analysis Coordinator Agent

analysis_coordinator = Agent(
    name="Analysis Coordinator",
    instructions="""You are the coordinator for Terraform analysis. Your responsibilities include:
    
    1. Coordinate analysis process:
       - Determine which specialized agents to use
       - Collect and combine analysis results
       - Prioritize recommendations
       - Create comprehensive reports
    
    2. Manage analysis workflow:
       - Security analysis
       - Cost optimization
       - Compliance checking
       - Performance optimization
       - Structure analysis
    
    3. Generate final reports:
       - Combine specialist findings
       - Prioritize recommendations
       - Provide implementation guidance
       - Highlight critical issues
    
    Coordinate with specialized agents and provide clear, actionable final recommendations.""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

# 2.3 Create Web Research Agent

terraform_researcher = Agent(
    name="Terraform Researcher",
    instructions="""You are a Terraform research expert who finds and analyzes information from the web. Your responsibilities include:
    
    1. Research Terraform best practices:
       - Search for latest Terraform patterns using search_terraform_info
       - Find official documentation and parse with fetch_and_parse_html
       - Gather community recommendations
       - Identify common solutions
    
    2. Research specific components:
       - Provider configurations
       - Resource specifications
       - Module patterns
       - Configuration examples
    
    3. Analyze and validate findings:
       - Verify information sources
       - Check version compatibility
       - Validate against official docs
       - Compare community solutions
    
    4. Provide research-based recommendations:
       - Best practice implementations
       - Common pitfalls to avoid
       - Version-specific considerations
       - Community-tested solutions
    
    Use web search tools to find relevant and up-to-date information:
    - Use search_terraform_info for initial searches
    - Use fetch_and_parse_html to get detailed content from URLs
    - Focus on official Terraform documentation and trusted sources
    - Validate information across multiple sources""",
    model=model,
    tools=[
        read_terraform_file,
        analyze_terraform_file,
        search_terraform_info,
        fetch_and_parse_html
    ]
)

# 2.4 Create Terraform Check Agent

terraform_checker = Agent(
    name="Terraform Checker",
    instructions="""You are a Terraform configuration validation expert. Your responsibilities include:
    
    1. Execute and analyze terraform check:
       - Run terraform check on specific files or entire configuration
       - Analyze check results in detail
       - Identify configuration issues
       - Validate resource dependencies
    
    2. Interpret check results:
       - Parse error messages and warnings
       - Identify root causes of issues
       - Explain problems in clear terms
       - Suggest specific fixes
    
    3. Provide validation reports:
       - Detailed check results
       - Configuration status
       - Identified issues
       - Required corrections
    
    4. Coordinate with other agents:
       - Share check results
       - Highlight security concerns
       - Flag performance issues
       - Identify compliance problems
    
    Always run terraform check before suggesting changes or applying configurations.
    Provide clear, actionable feedback about configuration validity.

    When showing commands:
    - Format executable commands as ```bash {{run}}
    command here
    ```
    - Format background commands as ```bash {{run:background}}
    command here
    ```
    - Use ```bash for command examples
    - Provide clear description before each command""",
    model=model,
    tools=[
        read_terraform_file,
        run_terraform_check,
        run_terminal_cmd
    ]
)

# Create TFVars Manager Agent
tfvars_manager = Agent(
    name="TFVars Manager",
    instructions="""You are a Terraform variables management expert. Your responsibilities include:
    
    1. Check terraform.tfvars status:
       - First verify if terraform.tfvars exists in output directory
       - If it exists during initial setup, DO NOT overwrite it
       - Read and report its current content
       - Handle updates when explicitly requested
    
    2. Handle new terraform.tfvars creation (ONLY if it doesn't exist):
       - Copy from terraform.tfvars.example
       - Identify required variables
       - Guide users through variable configuration
       - Create the file with user-provided values
    
    3. Variable validation and updates:
       - For existing files: validate current values
       - When update requested: update with new values
       - For new files: collect and validate new values
       - Ensure all required variables are set
       - Maintain proper variable formatting
    
    4. Update Management:
       - Accept and process update requests
       - Update specific variables when requested
       - Preserve existing values not being updated
       - Validate updated configuration
    
    5. Provide clear guidance:
       - If file exists: report current configuration
       - If updating: confirm changes made
       - If new file: explain required variables
       - Report any issues found
    
    6. Return Status:
       - Always return a clear status message about what was done
       - Include information about the current state of variables
       - If file exists: include current configuration
       - If new file: include what variables need to be set
       - Format response for the orchestrator to proceed
    
    When showing commands:
    - Format executable commands as ```bash {{run}}
    command here
    ```
    - Format background commands as ```bash {{run:background}}
    command here
    ```
    - Use ```bash for command examples
    - Provide clear description before each command
    
    IMPORTANT:
    - DO NOT overwrite existing terraform.tfvars during initial creation
    - DO update variables when explicitly requested to do so
    - Always validate variable values before and after updates
    - Return clear status messages about actions taken
    - DO NOT attempt to transfer control to other agents
    - Let the orchestrator handle all agent transitions""",
    model=model,
    tools=[
        manage_tfvars_file,
        update_tfvars_file,
        run_terminal_cmd
    ]
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
        terraform_editor,
        analysis_coordinator,
        security_analyzer,
        cost_optimizer,
        compliance_checker,
        performance_optimizer,
        structure_analyzer,
        terraform_researcher,
        terraform_checker,
        tfvars_manager
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
        1. Create/modify necessary .tf files
        2. Ensure proper file structure
        3. Include all required configurations
        4. Format commands properly:
           ```bash {{run}}
           terraform init
           ```
        
        IMPORTANT:
        - Create all files in the output directory
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