import subprocess
import os
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from .config import get_model_config
import logging

model = get_model_config()
logger = logging.getLogger(__name__)

# 1. Create Tools

@function_tool
def create_terraform_file(filename, content):
    """Create a new Terraform file with the specified content."""
    try:
        with open(filename, 'w') as f:
            f.write(content)
        return f"Successfully created Terraform file: {filename}"
    except Exception as e:
        return f"Error creating Terraform file: {str(e)}"

@function_tool
def delete_terraform_file(filename):
    """Delete a Terraform file."""
    try:
        os.remove(filename)
        return f"Successfully deleted Terraform file: {filename}"
    except Exception as e:
        return f"Error deleting Terraform file: {str(e)}"

@function_tool
def read_terraform_file(filename):
    """Read the contents of a Terraform file."""
    try:
        with open(filename, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading Terraform file: {str(e)}"

@function_tool
def run_terraform_plan():
    """Execute 'terraform plan' command."""
    try:
        result = subprocess.run(['terraform', 'plan'], 
                              capture_output=True, 
                              text=True)
        if result.returncode != 0:
            return f"Terraform plan failed:\n{result.stderr}"
        return f"Terraform plan output:\n{result.stdout}"
    except Exception as e:
        return f"Error running terraform plan: {str(e)}"

@function_tool
def run_terraform_apply():
    """Execute 'terraform apply' command with auto-approve."""
    try:
        result = subprocess.run(['terraform', 'apply', '-auto-approve'], 
                              capture_output=True, 
                              text=True)
        if result.returncode != 0:
            return f"Terraform apply failed:\n{result.stderr}"
        return f"Terraform apply output:\n{result.stdout}"
    except Exception as e:
        return f"Error running terraform apply: {str(e)}"

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

# 3. Create Main Orchestrator Agent

orchestrator_agent = Agent(
    name="Terraform Orchestrator",
    instructions="""You are the main orchestrator for Terraform operations. Your responsibilities include:

    1. Initial Analysis:
       - Analyze the user's request for Terraform operations
       - Validate the requested changes
       - Plan the appropriate steps to fulfill the request

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

    IMPORTANT: Always validate configurations before applying changes.
    Notify users of any potential risks or issues before proceeding with apply operations.
    """,
    tools=[
        create_terraform_file,
        delete_terraform_file,
        read_terraform_file,
        run_terraform_plan,
        run_terraform_apply
    ],
    model=model,
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[terraform_editor]
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
        3. Validate changes with terraform plan
        4. If apply is requested and plan is successful, run terraform apply
        5. Return detailed status of all operations

        IMPORTANT: 
        - Validate all changes before applying
        - Provide clear error messages if any issues occur
        - Ensure proper state management
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