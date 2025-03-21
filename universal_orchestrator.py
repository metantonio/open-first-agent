from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from duck_browser_agent.dds_agent import run_workflow as run_browser_workflow
from terraform_agent.terraform_agent import run_workflow as run_terraform_workflow
from dev_env_agent.dev_env_agent import run_workflow as run_dev_env_workflow
from aws_cli_agent.aws_cli_agent import run_workflow as run_aws_cli_workflow
from file_system_agent.file_system_agent import run_workflow as run_file_env_workflow
from terminal_agent import run_workflow as run_terminal_workflow
import logging
from config import get_model_config

model = get_model_config()
logger = logging.getLogger(__name__)

class UniversalOrchestrator:
    def __init__(self):
        self.orchestrator_agent = Agent(
            name="Universal Orchestrator",
            instructions="""You are the main orchestrator that coordinates all specialized agents. Your responsibilities include:

            1. Request Analysis:
               - Analyze user requests to determine which specialized agent to use
               - Route requests to the appropriate agent
               - Handle multi-agent scenarios when needed

            2. Agent Management:
               - Browser Agent: For web searches and content analysis
               - Terraform Agent: For infrastructure as code management
               - Development Environment Agent: For setting up development environments
               - AWS CLI Agent: For AWS CLI installation, configuration, and management
               - Terminal Agent: For executing terminal commands, file operations, and SSH connections
               - File Management Agent: For file system operations

            3. Response Coordination:
               - Collect and format responses from agents
               - Ensure consistent output format
               - Handle errors and provide clear feedback

            4. Context Management:
               - Maintain context across multiple requests
               - Track agent states and progress
               - Manage handoffs between agents

            IMPORTANT:
            - Always validate inputs before passing to agents
            - Provide clear error messages
            - Maintain consistent communication format
            """,
            model=model,
            model_settings=ModelSettings(temperature=0.1)
        )

    async def determine_agent(self, request: str) -> str:
        """Determine which agent should handle the request."""
        agent_response = await Runner.run(
            self.orchestrator_agent,
            f"""Analyze this request and determine which agent should handle it: {request}
            
            Available agents:
            1. Browser Agent - For web searches, news gathering, content analysis
            2. Terraform Agent - For infrastructure as code, terraform file management, terraform operations
            3. Development Environment Agent - For setting up development environments, IDE configuration, Python/Conda setup
            4. AWS CLI Agent - For AWS CLI installation, configuration, credentials management, and AWS connectivity testing
            5. File Management Agent - For file management, file search, file creation, file deletion, file editing, file copying, file moving
            6. Terminal Agent - For executing terminal commands, managing SSH connections, and performing file system operations
            
            Respond with either 'browser', 'terraform', 'dev_env', 'file_env', 'aws_cli', or 'terminal' based on the request content.
            """
        )
        return agent_response.final_output.strip().lower()

    async def process_request(self, request: str):
        """Process the user request using the appropriate agent."""
        try:
            agent_type = await self.determine_agent(request)
            logger.info(f"Determined agent type: {agent_type}")
            if agent_type == "browser":
                return run_browser_workflow(request)
            elif agent_type == "terraform":
                return run_terraform_workflow(request)
            elif agent_type == "dev_env":
                return run_dev_env_workflow(request)
            elif agent_type == "aws_cli":
                return run_aws_cli_workflow(request)
            elif agent_type == "file_env":
                return run_file_env_workflow(request)
            elif agent_type == "terminal":
                return run_terminal_workflow(request)
            else:
                return f"Error: Unknown agent type '{agent_type}'"
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return f"Error processing request: {str(e)}"

# Create a singleton instance
orchestrator = UniversalOrchestrator() 