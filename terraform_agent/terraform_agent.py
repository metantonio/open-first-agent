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
                current_vars = f.read()
            return {
                'status': 'exists',
                'message': 'terraform.tfvars already exists',
                'content': current_vars
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
                'message': 'terraform.tfvars created from example',
                'variables_needed': vars_needed
            }
        else:
            return {
                'status': 'error',
                'message': 'terraform.tfvars.example not found'
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
    1. Create well-structured Terraform configurations
    2. Follow Terraform best practices
    3. Include proper provider configurations
    4. Use clear resource naming
    5. Add appropriate tags and descriptions
    6. Implement proper variable declarations
    7. Follow security best practices
    8. Include necessary backend configuration
    
    Always format the Terraform code properly and include necessary comments.
    
    When creating or modifying Terraform files:
    1. Use create_terraform_file to create new files
    2. Use read_terraform_file to read existing files
    3. Ensure all configurations are properly formatted
    4. Include all necessary provider blocks
    5. Define required variables
    6. Configure resources with proper naming and tags""",
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
    
    1. Check and manage terraform.tfvars:
       - Verify if terraform.tfvars exists in output directory
       - Create from example if it doesn't exist
       - Identify required variables
       - Guide users through variable configuration
    
    2. Handle variable updates:
       - Validate variable values
       - Update terraform.tfvars with new values
       - Ensure proper formatting
       - Maintain variable consistency
    
    3. Provide clear guidance:
       - Explain required variables
       - Suggest appropriate values
       - Validate user input
       - Handle errors appropriately
    
    Always ensure terraform.tfvars is properly configured before any Terraform operations.""",
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

    1. Initial Analysis:
       - Analyze the user's request for Terraform operations
       - Validate the requested changes
       - Plan the appropriate steps to fulfill the request
       - For analysis requests, coordinate with the Analysis Coordinator
       - For research needs, coordinate with the Terraform Researcher
       - For configuration checks, use the Terraform Checker

    2. File Management:
       - Create new Terraform files when needed
       - Delete Terraform files when requested
       - Read and validate existing Terraform configurations
       - Ensure proper file structure and organization

    3. Terraform Operations:
       - Run terraform check to validate configurations
       - Run terraform plan to validate changes
       - Execute terraform apply when confirmed
       - Handle and report any errors appropriately
       - Ensure proper state management

    4. Quality Control:
       - Use Terraform Checker for configuration validation
       - Validate Terraform syntax
       - Check for security best practices
       - Ensure proper resource naming
       - Verify all required providers are configured
       - Handle errors and provide clear feedback

    5. Analysis and Recommendations:
       - Coordinate with Analysis Coordinator for reviews
       - Use Terraform Researcher for latest best practices
       - Present analysis results in a clear format
       - Prioritize recommendations based on impact
       - Provide implementation guidance for improvements

    6. Research and Documentation:
       - Use web research when needed
       - Find relevant documentation
       - Validate against current best practices
       - Incorporate community recommendations

    IMPORTANT: 
    - Always validate configurations with terraform check before other operations
    - Notify users of any potential risks or issues
    - Use web research to validate uncertain configurations
    - Ensure recommendations are based on current best practices
    - For analysis requests, ensure comprehensive review
    """,
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

        1. Analyze the request and determine required actions
        2. If research is needed, use the Terraform Researcher
        3. If creating/modifying files, use the terraform_editor
        4. Run terraform check using the Terraform Checker
        5. If analyzing existing files, use specialized analyzers
        6. Validate changes with terraform plan when needed
        7. If apply is requested and plan is successful, run terraform apply
        8. Return detailed status of all operations

        IMPORTANT: 
        - Always run terraform check before other operations
        - Research uncertain configurations
        - Validate all changes before applying
        - Provide clear error messages if any issues occur
        - Ensure proper state management
        - Follow security best practices
        - For analysis requests, provide comprehensive recommendations

        Handle all steps appropriately and provide detailed feedback.
        """
    )
    
    return orchestrator_response.final_output

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_request = "Create a basic AWS EC2 instance configuration"
    print(f"Running test with request: {test_request}")
    print(run_workflow(test_request)) 