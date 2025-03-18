import subprocess
import os
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from .config import get_model_config
import logging
import json
import re
import platform

model = get_model_config()
logger = logging.getLogger(__name__)

# Ensure output directory exists for logs and configs
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_working_directory() -> str:
    """Get the output directory path."""
    return OUTPUT_DIR

# 1. Create Tools

@function_tool
def check_aws_cli_installation():
    """Check if AWS CLI is installed and get its version."""
    try:
        result = subprocess.run(['aws', '--version'], 
                              capture_output=True, 
                              text=True)
        if result.returncode == 0:
            return {
                'installed': True,
                'version': result.stdout.strip(),
                'message': 'AWS CLI is installed'
            }
        return {
            'installed': False,
            'version': None,
            'message': 'AWS CLI is not installed'
        }
    except Exception as e:
        return {
            'installed': False,
            'version': None,
            'message': f'Error checking AWS CLI: {str(e)}'
        }

@function_tool
def install_aws_cli():
    """Install AWS CLI based on the operating system."""
    os_name = platform.system().lower()
    
    try:
        if os_name == "darwin":  # macOS
            # Use brew to install AWS CLI
            result = subprocess.run(['brew', 'install', 'awscli'],
                                  capture_output=True,
                                  text=True)
        elif os_name == "linux":
            # Use apt for Ubuntu/Debian
            result = subprocess.run(['sudo', 'apt-get', 'update'],
                                  capture_output=True,
                                  text=True)
            if result.returncode == 0:
                result = subprocess.run(['sudo', 'apt-get', 'install', '-y', 'awscli'],
                                      capture_output=True,
                                      text=True)
        else:
            return {
                'success': False,
                'message': f'Unsupported operating system: {os_name}'
            }
            
        if result.returncode == 0:
            return {
                'success': True,
                'message': 'AWS CLI installed successfully'
            }
        else:
            return {
                'success': False,
                'message': f'Failed to install AWS CLI: {result.stderr}'
            }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error installing AWS CLI: {str(e)}'
        }

@function_tool
def configure_aws_cli(aws_access_key_id: str, aws_secret_access_key: str, region: str, output_format: str = 'json'):
    """Configure AWS CLI with credentials and settings."""
    try:
        # Create AWS credentials file
        credentials_dir = os.path.expanduser('~/.aws')
        os.makedirs(credentials_dir, exist_ok=True)
        
        # Write credentials file
        credentials_file = os.path.join(credentials_dir, 'credentials')
        with open(credentials_file, 'w') as f:
            f.write(f"""[default]
aws_access_key_id = {aws_access_key_id}
aws_secret_access_key = {aws_secret_access_key}
""")
        
        # Write config file
        config_file = os.path.join(credentials_dir, 'config')
        with open(config_file, 'w') as f:
            f.write(f"""[default]
region = {region}
output = {output_format}
""")
        
        # Set proper permissions
        os.chmod(credentials_file, 0o600)
        os.chmod(config_file, 0o600)
        
        return {
            'success': True,
            'message': 'AWS CLI configured successfully',
            'config_path': credentials_dir
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error configuring AWS CLI: {str(e)}'
        }

@function_tool
def configure_aws_cli_sso(sso_start_url: str, sso_account_id: str, sso_role_name: str = "EC2-Terraform", 
                         region: str = "us-east-1", output_format: str = "json"):
    """Configure AWS CLI with SSO credentials and settings."""
    try:
        # Create AWS credentials directory
        credentials_dir = os.path.expanduser('~/.aws')
        os.makedirs(credentials_dir, exist_ok=True)
        
        # Write config file with SSO configuration
        config_file = os.path.join(credentials_dir, 'config')
        with open(config_file, 'w') as f:
            f.write(f"""[default]
sso_session = aws
sso_account_id = {sso_account_id}
sso_role_name = {sso_role_name}
region = {region}
output = {output_format}

[sso-session aws]
sso_start_url = {sso_start_url}
sso_region = {region}
sso_registration_scopes = sso:account:access
""")
        
        # Set proper permissions
        os.chmod(config_file, 0o600)
        
        return {
            'success': True,
            'message': 'AWS CLI SSO configuration completed successfully',
            'config_path': config_file
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error configuring AWS CLI SSO: {str(e)}'
        }

@function_tool
def check_aws_configuration():
    """Check current AWS CLI configuration."""
    try:
        # Check credentials
        result = subprocess.run(['aws', 'configure', 'list'],
                              capture_output=True,
                              text=True)
        
        # Get current region
        region_result = subprocess.run(['aws', 'configure', 'get', 'region'],
                                     capture_output=True,
                                     text=True)
        
        return {
            'success': result.returncode == 0,
            'config_status': result.stdout,
            'current_region': region_result.stdout.strip() if region_result.returncode == 0 else None,
            'message': 'Configuration retrieved successfully' if result.returncode == 0 else 'Failed to get configuration'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error checking AWS configuration: {str(e)}'
        }

@function_tool
def test_aws_connection():
    """Test AWS connection by listing S3 buckets."""
    try:
        result = subprocess.run(['aws', 's3', 'ls'],
                              capture_output=True,
                              text=True)
        
        return {
            'success': result.returncode == 0,
            'output': result.stdout if result.returncode == 0 else result.stderr,
            'message': 'Connection successful' if result.returncode == 0 else 'Connection failed'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error testing AWS connection: {str(e)}'
        }

@function_tool
def show_config_format():
    """Show the required format for AWS CLI configuration."""
    return {
        'standard_config': """# Standard AWS CLI configuration format:
[default]
region = us-east-1
output = json

# Required parameters:
- region: AWS region (e.g., us-east-1, us-west-2)
- output: Output format (json, text, table)""",

        'sso_config': """# AWS CLI SSO configuration format:
[default]
sso_session = aws
sso_account_id = YOUR_ACCOUNT_ID
sso_role_name = EC2-Terraform
region = us-east-1
output = json

[sso-session aws]
sso_start_url = YOUR_SSO_START_URL
sso_region = us-east-1
sso_registration_scopes = sso:account:access

# Required parameters for SSO:
- sso_start_url: Your AWS SSO start URL
- sso_account_id: Your AWS account ID
- sso_role_name: Role name (default: EC2-Terraform)
- region: AWS region (default: us-east-1)
- output: Output format (default: json)""",

        'credentials_config': """# AWS CLI credentials format (for non-SSO):
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY

# Required parameters:
- aws_access_key_id: Your AWS access key
- aws_secret_access_key: Your AWS secret key"""
    }

# 2. Create Specialized Agents

installation_checker = Agent(
    name="AWS CLI Installation Checker",
    instructions="""You are an AWS CLI installation verification expert. Your responsibilities include:
    
    1. Check AWS CLI Installation:
       - Verify if AWS CLI is installed
       - Check version information
       - Report installation status
       - Provide clear feedback
    
    2. Command Formatting and Results:
       First show the command:
       ```bash {{run}}
       aws --version
       ```
       
       Then show the result after execution:
       "Command output: <actual output from command>"
    
    IMPORTANT:
    - Always check installation status first
    - Show both command and its output
    - Provide clear version information
    - Format commands with {{run}} tags
    - Never use numbered action IDs
    - Always use "run" as the action name""",
    model=model,
    tools=[check_aws_cli_installation]
)

installation_manager = Agent(
    name="AWS CLI Installation Manager",
    instructions="""You are an AWS CLI installation expert. Your responsibilities include:
    
    1. Install AWS CLI:
       - Handle OS-specific installation
       - Verify installation success
       - Report installation results
       - Handle errors appropriately
    
    2. Command Formatting and Results:
       First show the installation command:
       ```bash {{run}}
       command here
       ```
       
       Then show the result:
       "Installation result: <actual output from command>"
    
    IMPORTANT:
    - Handle OS-specific requirements
    - Show both command and result
    - Verify installation success
    - Format commands with {{run}} tags
    - Never use numbered action IDs
    - Always use "run" as the action name""",
    model=model,
    tools=[install_aws_cli]
)

connection_tester = Agent(
    name="AWS CLI Connection Tester",
    instructions="""You are an AWS CLI connection testing expert. Your responsibilities include:
    
    1. Test AWS Connection:
       - Check AWS credentials
       - Test S3 connectivity
       - Verify configuration
       - Report connection status
    
    2. Command Formatting and Results:
       First check configuration:
       ```bash {{run}}
       aws configure list
       ```
       Show result: "Configuration status: <actual output>"
       
       Then test connection:
       ```bash {{run}}
       aws s3 ls
       ```
       Show result: "Connection test result: <actual output>"
    
    IMPORTANT:
    - Test basic connectivity first
    - Show both commands and their outputs
    - Check configuration status
    - Format commands with {{run}} tags
    - Never use numbered action IDs
    - Always use "run" as the action name""",
    model=model,
    tools=[test_aws_connection, check_aws_configuration]
)

configuration_manager = Agent(
    name="AWS CLI Configuration Manager",
    instructions="""You are an AWS CLI configuration expert. Your responsibilities include:
    
    1. Manage AWS Configuration:
       - Handle credentials setup
       - Configure AWS settings
       - Set up SSO if needed
       - Manage config files
    
    2. Command Formatting and Results:
       First show the configuration check:
       ```bash {{run}}
       aws configure list
       ```
       Show result: "Current configuration: <actual output>"
       
       If changes needed, show configuration commands and their results
    
    IMPORTANT:
    - Handle both standard and SSO config
    - Show both commands and their outputs
    - Secure credential storage
    - Format commands with {{run}} tags
    - Never use numbered action IDs
    - Always use "run" as the action name""",
    model=model,
    tools=[configure_aws_cli, configure_aws_cli_sso, show_config_format]
)

# Update the main AWS CLI agent to be an orchestrator
aws_cli_agent = Agent(
    name="AWS CLI Orchestrator",
    instructions="""You are the main orchestrator for AWS CLI operations. Your responsibilities include:

    1. Coordinate Between Specialized Agents:
       - Use installation_checker for installation verification
       - Use installation_manager for installation tasks
       - Use connection_tester for connectivity tests
       - Use configuration_manager for setup tasks
    
    2. Workflow Management:
       - Start with installation check
       - Handle installation if needed
       - Proceed to configuration tasks
       - End with connection testing
    
    3. Results Presentation:
       - Show each command executed
       - Display command outputs
       - Provide clear summaries
       - Include error messages if any
    
    4. Command Formatting:
       Show commands and their results:
       ```bash {{run}}
       command here
       ```
       "Result: <actual output>"
    
    IMPORTANT:
    - Coordinate agent transitions
    - Show all command outputs
    - Maintain workflow state
    - Format commands with {{run}} tags
    - Never use numbered action IDs
    - Always use "run" as the action name""",
    model=model,
    tools=[
        check_aws_cli_installation,
        install_aws_cli,
        configure_aws_cli,
        configure_aws_cli_sso,
        check_aws_configuration,
        test_aws_connection,
        show_config_format
    ],
    handoffs=[
        installation_checker,
        installation_manager,
        connection_tester,
        configuration_manager
    ]
)

# 3. Main workflow function

def run_workflow(request):
    """Run the AWS CLI workflow with specialized agents."""
    logger.info(f"Starting AWS CLI workflow for request: {request}")
    
    # First, check installation
    installation_check = Runner.run_sync(
        installation_checker,
        """Check if AWS CLI is installed and get version information.
        Show the command used and its output."""
    )
    logger.info("Installation Check Response: %s", installation_check.final_output)
    
    # If installation needed, handle it
    if "not installed" in installation_check.final_output.lower():
        installation_result = Runner.run_sync(
            installation_manager,
            """Install AWS CLI for the current operating system.
            Show the installation command and its result."""
        )
        logger.info("Installation Result: %s", installation_result.final_output)
    
    # Test connection and configuration
    connection_test = Runner.run_sync(
        connection_tester,
        """Test AWS connection and verify configuration.
        Show all commands executed and their outputs."""
    )
    logger.info("Connection Test Response: %s", connection_test.final_output)
    
    # Use orchestrator for final response
    final_response = Runner.run_sync(
        aws_cli_agent,
        f"""Provide a final response for this request: {request}
        
        Context:
        - Installation Status: {installation_check.final_output}
        - Connection Status: {connection_test.final_output}
        
        IMPORTANT:
        - Summarize all results
        - Include all command outputs
        - Format any commands with {{run}} tags
        - Never use numbered action IDs
        - Always use "run" as the action name"""
    )
    
    return final_response.final_output

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_request = "Check AWS CLI installation and configuration"
    print(f"Running test with request: {test_request}")
    print(run_workflow(test_request)) 