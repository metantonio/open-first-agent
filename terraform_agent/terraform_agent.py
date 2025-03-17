import subprocess
import os
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from .config import get_model_config
import logging

model = get_model_config()
logger = logging.getLogger(__name__)

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
    
    Always format the Terraform code properly and include necessary comments.""",
    model=model
)

# 2.1 Create Analyzer Agent for Terraform

terraform_analyzer = Agent(
    name="Terraform Analyzer",
    instructions="""You are a Terraform analysis and optimization expert. Your responsibilities include analyzing Terraform configurations and providing recommendations based on best practices and the provided example configuration.

    1. Compare with Example Configuration:
       - Use the example configuration (provided in analysis_results['example']) as a reference
       - Identify missing best practices from the example
       - Suggest improvements based on the example patterns
       - Recommend additional security measures shown in the example
       
    2. Analyze existing Terraform configurations for:
       - Security best practices (like encryption, IMDSv2, minimal permissions)
       - Resource optimization opportunities (like using gp3 vs gp2)
       - Cost optimization recommendations (like t3 vs t2 instances)
       - Performance improvements
       - Maintainability improvements
       - Compliance with company standards
       
    3. Check for Key Components (based on example):
       - Provider configuration with proper version constraints
       - Backend configuration for state management
       - Variable declarations with descriptions and constraints
       - Resource configurations with best practices
       - Security group rules with proper restrictions
       - Proper tagging strategy
       - Lifecycle rules where appropriate
       - Output definitions for important values
       
    4. Provide detailed recommendations for:
       - Security enhancements (based on example patterns)
       - Cost savings opportunities
       - Performance optimizations
       - Best practices implementation
       - Code structure improvements
       
    5. Review and validate:
       - Resource configurations against example
       - Variable usage patterns
       - Provider configurations
       - Backend configurations
       - Module structure
       - Naming conventions
       - Tagging strategies
       
    6. Generate comprehensive reports that include:
       - Comparison with example configuration
       - Current state analysis
       - Identified gaps from best practices
       - Prioritized recommendations
       - Implementation suggestions
       - Potential risks and mitigation strategies
       
    Always provide clear, actionable recommendations with explanations of their benefits and potential impacts.
    Use the example configuration as a guide for suggesting improvements.""",
    model=model,
    tools=[read_terraform_file, analyze_terraform_file]
)

# 3. Create Main Orchestrator Agent

orchestrator_agent = Agent(
    name="Terraform Orchestrator",
    instructions="""You are the main orchestrator for Terraform operations. Your responsibilities include:

    1. Initial Analysis:
       - Analyze the user's request for Terraform operations
       - Validate the requested changes
       - Plan the appropriate steps to fulfill the request
       - For analysis requests, coordinate with the Terraform Analyzer

    2. File Management:
       - Create new Terraform files when needed
       - Delete Terraform files when requested
       - Read and validate existing Terraform configurations
       - Ensure proper file structure and organization

    3. Terraform Operations:
       - Run terraform plan to validate changes
       - Execute terraform apply when confirmed
       - Handle and report any errors appropriately
       - Ensure proper state management

    4. Quality Control:
       - Validate Terraform syntax
       - Check for security best practices
       - Ensure proper resource naming
       - Verify all required providers are configured
       - Handle errors and provide clear feedback

    5. Analysis and Recommendations:
       - Coordinate with Terraform Analyzer for configuration reviews
       - Present analysis results in a clear format
       - Prioritize recommendations based on impact
       - Provide implementation guidance for suggested improvements

    IMPORTANT: Always validate configurations before applying changes.
    Notify users of any potential risks or issues before proceeding with apply operations.
    For analysis requests, ensure comprehensive review and clear recommendations.
    """,
    tools=[
        create_terraform_file,
        delete_terraform_file,
        read_terraform_file,
        run_terraform_plan,
        run_terraform_apply,
        analyze_terraform_file
    ],
    model=model,
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[terraform_editor, terraform_analyzer]
)

# 4. Main workflow function

def run_workflow(request):
    """Run the Terraform workflow with the orchestrator as the main controller."""
    logger.info(f"Starting Terraform workflow for request: {request}")
    
    orchestrator_response = Runner.run_sync(
        orchestrator_agent,
        f"""Process this Terraform request: {request}

        1. Analyze the request and determine required actions
        2. If creating/modifying files, use the terraform_editor for proper formatting
        3. If analyzing existing files, use the terraform_analyzer for recommendations
        4. Validate changes with terraform plan when needed
        5. If apply is requested and plan is successful, run terraform apply
        6. Return detailed status of all operations

        IMPORTANT: 
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