import unittest
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from agents import Runner
from aws_cli_agent import (
    run_workflow,
    aws_cli_agent,
    connection_tester,
    installation_checker,
    installation_manager
)
# Load environment variables from .env file
env_path = Path('..') / '.env'
print(env_path)
load_dotenv(dotenv_path=env_path, override=True)

# Verify and export critical environment variables
if not os.getenv('OPENAI_API_KEY'):
    raise EnvironmentError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

# Ensure OPENAI_API_KEY is explicitly set in the environment
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

class TestAWSCLIAGent(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    """ 
        async def test_check_aws_cli_installation(self):
            result = await Runner.run(installation_checker, "Check AWS CLI installation")
            self.assertIn('installed', result.final_output)
            self.assertIn('version', result.final_output)
            self.assertIn('message', result.final_output)

        async def test_install_aws_cli(self):
            result = await Runner.run(installation_manager, "Install AWS CLI")
            self.assertIn('success', result.final_output)
            self.assertIn('message', result.final_output)

        async def test_configure_aws_cli(self):
            result = await Runner.run(installation_manager, f" access key: {key}, secret key: {secret}, region: us-east-1")
            self.assertIn('success', result.final_output)
            self.assertIn('message', result.final_output)
            self.assertIn('config_path', result.final_output)
    """

    """ 
    async def test_configure_aws_cli_sso(self):
        result = await run_workflow('test aws configuration with sso profile 123456789012')
        self.assertIn('success', result)
        self.assertIn('message', result)
        self.assertIn('config_path', result)
    """


    def test_test_aws_connection(self):
        #result = await Runner.run(connection_tester, "Check AWS connection")
        result = self.loop.run_until_complete(Runner.run(
            connection_tester,
            "Check AWS connection"
        ))
        # Assuming result has attributes like success, output, and message
        #self.assertIn('success', result.final_output)  # Check if 'success' is in the final output
        #self.assertIn('output', result.final_output)   # Check if 'output' is in the final output
        self.assertIn('Connection test result', result.final_output) 
        self.assertIn('Connection status', result.final_output) 


if __name__ == '__main__':
    unittest.main() 