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
    5. Validate configurations with terraform check
    
    IMPORTANT:
    - All files must be created in the output directory
    - Coordinate with tfvars_manager for variable values
    - Ensure all dependencies are properly declared
    - Follow security best practices""",
    model=model,
    tools=[
        create_terraform_file,
        read_terraform_file,
        delete_terraform_file,
        run_terraform_check,
        run_terraform_init
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
    Provide clear, actionable feedback about configuration validity.""",
    model=model,
    tools=[
        read_terraform_file,
        run_terraform_check
    ]
)

# Create TFVars Manager Agent
tfvars_manager = Agent(
    name="TFVars Manager",
    instructions="""You are a Terraform variables management expert. Your responsibilities include:
    
    1. Check terraform.tfvars status:
       - First verify if terraform.tfvars exists in output directory
       - If it exists, DO NOT modify or recreate it
       - Only read and report its current content
       - If it doesn't exist, then proceed with creation
    
    2. Handle new terraform.tfvars creation (ONLY if it doesn't exist):
       - Copy from terraform.tfvars.example
       - Identify required variables
       - Guide users through variable configuration
       - Create the file with user-provided values
    
    3. Variable validation and updates:
       - For existing files: only validate current values
       - For new files: collect and validate new values
       - Ensure all required variables are set
       - Maintain proper variable formatting
    
    4. Provide clear guidance:
       - If file exists: report current configuration
       - If new file: explain required variables
       - Validate all variable values
       - Report any issues found
    
    IMPORTANT:
    - NEVER modify an existing terraform.tfvars file unless explicitly requested
    - Only create new terraform.tfvars if it doesn't exist
    - Always validate variable values regardless of file status
    - Provide clear status updates about the file state""",
    model=model,
    tools=[
        manage_tfvars_file,
        update_tfvars_file
    ]
)

# 3. Create Main Orchestrator Agent

orchestrator_agent = Agent(
    name="Terraform Orchestrator",
    instructions="""You are the main orchestrator for Terraform operations. Your responsibilities include:

    1. Initial Setup and Validation:
       - FIRST check and setup terraform.tfvars using tfvars_manager
       - Ensure output directory exists and is properly configured
       - Validate environment readiness
       - Check for required dependencies
    
    2. File Creation and Management:
       - Use terraform_editor to create initial .tf files
       - Ensure all files are created in output directory
       - Maintain proper file organization
       - Handle file dependencies correctly

    3. Variable Management:
       - Coordinate with tfvars_manager for variable setup
       - Ensure all required variables are defined
       - Validate variable values
       - Maintain variable consistency

    4. Configuration Validation:
       - Use Terraform Checker for configuration validation
       - Run terraform check before operations
       - Validate syntax and structure
       - Verify resource dependencies

    5. Terraform Operations:
       - Execute terraform init when needed
       - Run terraform plan to preview changes
       - Execute terraform apply when confirmed
       - Handle state management properly

    6. Analysis and Recommendations:
       - Use Analysis Coordinator for reviews
       - Coordinate with specialized analyzers
       - Provide clear recommendations
       - Prioritize improvements

    7. Research and Documentation:
       - Use Terraform Researcher for best practices
       - Find relevant documentation
       - Validate configurations
       - Incorporate community recommendations

    IMPORTANT: 
    - ALWAYS start by checking/setting up terraform.tfvars
    - Ensure all files are created in output directory
    - Validate configurations before operations
    - Follow security best practices
    - Provide clear error messages
    - For new configurations, follow this order:
      1. Setup tfvars
      2. Create main.tf
      3. Create variables.tf
      4. Create outputs.tf (if needed)
      5. Initialize and validate""",
    tools=[
        create_terraform_file,
        delete_terraform_file,
        read_terraform_file,
        run_terraform_check,
        run_terraform_plan,
        run_terraform_apply,
        analyze_terraform_file,
        manage_tfvars_file,
        update_tfvars_file
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
    
    orchestrator_response = Runner.run_sync(
        orchestrator_agent,
        f"""Process this Terraform request: {request}

        Follow these steps in order:
        1. Check and setup terraform.tfvars first
           - Use tfvars_manager to check/create terraform.tfvars
           - Get required variables from user if needed
        
        2. Create or modify Terraform files
           - Use terraform_editor for file creation
           - Ensure all files are in output directory
           - Follow proper file structure
        
        3. Validate configurations
           - Run terraform check
           - Verify syntax and structure
           - Check for errors
        
        4. Execute Terraform operations if needed
           - Run terraform init for new configurations
           - Run terraform plan if changes made
           - Run terraform apply if requested
        
        5. Provide analysis and recommendations
           - Use specialized analyzers if needed
           - Give clear feedback on actions taken
           - Suggest improvements if applicable

        IMPORTANT: 
        - ALWAYS start with tfvars setup
        - Create all files in output directory
        - Validate before operations
        - Provide clear error messages
        - Follow security best practices

        Handle all steps appropriately and provide detailed feedback.
        """
    )
    
    return orchestrator_response.final_output

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_request = "Create a basic AWS EC2 instance configuration"
    print(f"Running test with request: {test_request}")
    print(run_workflow(test_request)) 