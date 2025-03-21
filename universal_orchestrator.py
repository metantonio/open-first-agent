from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from duck_browser_agent.dds_agent import run_workflow as run_browser_workflow
from terraform_agent.terraform_agent import run_workflow as run_terraform_workflow
from dev_env_agent.dev_env_agent import run_workflow as run_dev_env_workflow
from aws_cli_agent.aws_cli_agent import run_workflow as run_aws_cli_workflow
from file_system_agent.file_system_agent import run_workflow as run_file_env_workflow
from terminal_agent.terminal_task_agent import run_workflow as run_terminal_workflow
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

            2. Agent Selection Rules:
               Terminal Agent (Select for any of these tasks):
               - File operations (create, copy, move, delete files/directories)
               - Directory operations (list contents, create, delete directories)
               - File searching or pattern matching
               - Terminal commands execution
               - SSH connections and operations
               - Any local system operations
               
               Browser Agent:
               - Web searches and research
               - Content analysis from websites
               - News gathering
               - Documentation lookup
               
               Terraform Agent:
               - Infrastructure as code management
               - Terraform file operations
               - Terraform commands and workflows
               
               Development Environment Agent:
               - Development environment setup
               - IDE configuration
               - Python/Conda environment management
               
               AWS CLI Agent:
               - AWS CLI installation and setup
               - AWS credentials management
               - AWS connectivity testing

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
            f"""Analyze the following request and respond ONLY with the appropriate agent type in lowercase.

            Request: {request}

            Valid responses:
            - 'terminal': For file operations (create/copy/delete/list files), directory operations, terminal commands, SSH
            - 'browser': For web searches, content analysis, documentation
            - 'terraform': For infrastructure as code, terraform operations
            - 'dev_env': For development environment setup, IDE config
            - 'aws_cli': For AWS CLI setup and configuration

            Terminal Agent Keywords:
            - file, directory, folder, path, copy, move, delete, create, list, contents, find, search
            - ssh, terminal, command, execute, run
            - local, system, operation

            Response format: Just the agent type in lowercase, nothing else.
            """,
            context={"request": request}
        )
        
        # Extract just the agent type from the response
        agent_type = agent_response.final_output.strip().lower()
        
        # Validate the agent type
        valid_agents = {'browser', 'terraform', 'dev_env', 'aws_cli', 'terminal'}
        if agent_type not in valid_agents:
            logger.warning(f"Invalid agent type returned: {agent_type}, defaulting to terminal")
            # Default to terminal agent for unrecognized operations
            return 'terminal'
            
        logger.info(f"Selected agent type: {agent_type} for request: {request}")
        return agent_type

    async def process_request(self, request: str):
        """Process the user request using the appropriate agent."""
        try:
            # Handle Chainlit Message objects
            if hasattr(request, 'content'):
                request = request.content
            elif not isinstance(request, str):
                request = str(request)

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
            #elif agent_type == "file_env":
            #    return run_file_env_workflow(request)
            elif agent_type == "terminal":
                return run_terminal_workflow(request)
            else:
                return f"Error: Unknown agent type '{agent_type}'"
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return f"Error processing request: {str(e)}"

# Create a singleton instance
orchestrator = UniversalOrchestrator() 