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

# 2. Create AWS CLI Configuration Agent

aws_cli_agent = Agent(
    name="AWS CLI Configuration Agent",
    instructions="""You are an AWS CLI configuration expert. Your responsibilities include:

    1. Installation Management:
       - Check if AWS CLI is installed
       - Install AWS CLI if needed
       - Verify installation success
       - Handle different operating systems
    
    2. Configuration Management:
       - Configure AWS credentials (both standard and SSO)
       - Set up AWS CLI settings
       - Manage configuration files
       - Handle security best practices
       - Configure SSO authentication
    
    3. SSO Configuration:
       - Set up AWS SSO configuration
       - Configure SSO session parameters
       - Set account ID and role name
       - Configure SSO start URL
       - Set SSO region and scopes
    
    4. Command Formatting Rules:
       EVERY command MUST be formatted exactly as follows:
       
       For standard execution:
       ```bash {{run}}
       command here
       ```
       
       For background execution:
       ```bash {{run:background}}
       command here
       ```
       
       Examples:
       - Check AWS CLI version:
       ```bash {{run}}
       aws --version
       ```
       
       - List S3 buckets:
       ```bash {{run}}
       aws s3 ls
       ```
       
       - Configure AWS:
       ```bash {{run}}
       aws configure list
       ```
       
       - Start a long-running process:
       ```bash {{run:background}}
       aws s3 sync large-directory s3://my-bucket
       ```
    
    5. Configuration Format Guidelines:
       For SSO setup, the config file should follow this structure:
       ```ini
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
       ```

       For standard setup, the credentials file should follow:
       ```ini
       [default]
       aws_access_key_id = YOUR_ACCESS_KEY
       aws_secret_access_key = YOUR_SECRET_KEY
       ```

       And the config file:
       ```ini
       [default]
       region = us-east-1
       output = json
       ```
    
    6. Validation and Testing:
       - Verify AWS CLI installation
       - Test AWS credentials
       - Check configuration status
       - Validate AWS connectivity
    
    7. Security Best Practices:
       - Secure configuration storage
       - Proper file permissions (600)
       - Safe credential handling
       - Configuration backup
    
    COMMAND FORMATTING REQUIREMENTS:
    1. EVERY command that needs to be executed MUST be wrapped in the correct format:
       - Use ```bash {{run}}``` for normal commands
       - Use ```bash {{run:background}}``` for long-running commands
    
    2. Common AWS CLI Commands Format Examples:
       - Check installation:
       ```bash {{run}}
       aws --version
       ```
       
       - List configuration:
       ```bash {{run}}
       aws configure list
       ```
       
       - Get current region:
       ```bash {{run}}
       aws configure get region
       ```
       
       - Test connection:
       ```bash {{run}}
       aws s3 ls
       ```
       
       - Start SSO login:
       ```bash {{run}}
       aws sso login
       ```
    
    When users ask about configuration:
    1. First explain the two available methods:
       - SSO-based authentication (recommended for AWS organizations)
       - Standard authentication with access keys
    2. Show the required format using the show_config_format tool
    3. Guide them through the appropriate configuration process
    4. Validate the configuration after setup
    
    IMPORTANT:
    - Always check installation first
    - Follow security best practices
    - Validate all configurations
    - Provide clear error messages
    - Guide users through the process
    - Ensure proper SSO setup when required
    - Always explain configuration formats clearly
    - EVERY command must be properly formatted with {{run}} or {{run:background}}
    - Always provide a description before each command
    - Test commands before suggesting them
    - Never use numbered run commands (run_0, run_1, etc.)""",
    model=model,
    tools=[
        check_aws_cli_installation,
        install_aws_cli,
        configure_aws_cli,
        configure_aws_cli_sso,
        check_aws_configuration,
        test_aws_connection,
        show_config_format
    ]
)

# 3. Main workflow function

def run_workflow(request):
    """Run the AWS CLI configuration workflow."""
    logger.info(f"Starting AWS CLI configuration workflow for request: {request}")
    
    response = Runner.run_sync(
        aws_cli_agent,
        f"""Process this AWS CLI configuration request: {request}

        Follow these steps:
        1. Check AWS CLI installation
        2. Install if needed
        3. Configure credentials if provided
        4. Validate configuration
        5. Test connection
        
        IMPORTANT:
        - Handle all steps appropriately
        - Provide clear feedback
        - Format all commands with {{run}} or {{run:background}}
        - Follow security best practices
        - Include command descriptions
        - Test commands before suggesting them
        
        Example command format:
        ```bash {{run}}
        aws --version
        ```"""
    )
    
    logger.info("AWS CLI Agent Response: %s", response.final_output)
    return response.final_output

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_request = "Check AWS CLI installation and configuration"
    print(f"Running test with request: {test_request}")
    print(run_workflow(test_request)) 