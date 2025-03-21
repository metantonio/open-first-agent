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
               - Analyze user requests to identify required agents and sequence
               - Break down complex requests into sub-tasks
               - Determine optimal agent sequence for multi-step operations
               - Route sub-tasks to appropriate agents

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

            3. Multi-Agent Workflow Rules:
               - Identify dependencies between sub-tasks
               - Execute agents in correct sequence
               - Pass context between agents
               - Verify each step's completion before proceeding
               - Handle errors at any step appropriately

            4. Common Multi-Agent Scenarios:
               - Setup & Configuration:
                 1. Browser Agent (research requirements)
                 2. Dev Env Agent (setup environment)
                 3. Terminal Agent (local configuration)
               
               - Infrastructure Tasks:
                 1. Browser Agent (lookup documentation)
                 2. Terraform Agent (infrastructure code)
                 3. AWS CLI Agent (credentials/testing)
               
               - Development Tasks:
                 1. Terminal Agent (file operations)
                 2. Dev Env Agent (environment setup)
                 3. Browser Agent (documentation lookup)

            IMPORTANT:
            - Always validate inputs before passing to agents
            - Maintain state across multi-agent workflows
            - Provide clear error messages
            - Ensure proper handoff between agents
            """,
            model=model,
            model_settings=ModelSettings(temperature=0.1)
        )

    async def analyze_workflow(self, request: str) -> list:
        """Analyze request to determine required agents and sequence."""
        workflow_response = await Runner.run(
            self.orchestrator_agent,
            f"""Analyze the following request and determine which agents are needed and in what order.
            Return the response as a comma-separated list of agent types in execution order.

            Request: {request}

            Available agents:
            - terminal: File operations, commands, SSH
            - browser: Web searches, documentation
            - terraform: Infrastructure as code
            - dev_env: Development environment setup
            - aws_cli: AWS CLI management

            Example responses:
            - "terminal" (for single agent)
            - "browser,terminal" (for multi-agent sequence)
            - "browser,terraform,aws_cli" (for complex workflow)

            Response format: Just the comma-separated agent types, nothing else.
            """,
            context={"request": request}
        )
        
        # Parse the workflow sequence
        agent_sequence = [agent.strip() for agent in workflow_response.final_output.strip().lower().split(',')]
        
        # Validate agent types
        valid_agents = {'browser', 'terraform', 'dev_env', 'aws_cli', 'terminal'}
        agent_sequence = [agent for agent in agent_sequence if agent in valid_agents]
        
        # Default to terminal if no valid agents
        if not agent_sequence:
            logger.warning(f"No valid agents in sequence, defaulting to terminal")
            return ['terminal']
            
        logger.info(f"Determined agent sequence: {agent_sequence} for request: {request}")
        return agent_sequence

    async def process_request(self, request: str):
        """Process the user request using the appropriate agent sequence."""
        try:
            # Handle Chainlit Message objects
            if hasattr(request, 'content'):
                request = request.content
            elif not isinstance(request, str):
                request = str(request)

            # Analyze workflow to get agent sequence
            agent_sequence = await self.analyze_workflow(request)
            logger.info(f"Processing request with agent sequence: {agent_sequence}")
            
            # Execute agents in sequence
            result = None
            for agent_type in agent_sequence:
                logger.info(f"Executing agent: {agent_type}")
                
                if agent_type == "browser":
                    result = run_browser_workflow(request)
                elif agent_type == "terraform":
                    result = run_terraform_workflow(request)
                elif agent_type == "dev_env":
                    result = run_dev_env_workflow(request)
                elif agent_type == "aws_cli":
                    result = run_aws_cli_workflow(request)
                elif agent_type == "terminal":
                    result = run_terminal_workflow(request)
                
                # Update request with result for context if needed
                if isinstance(result, dict) and result.get('context'):
                    request = f"{request}\nContext: {result['context']}"
            
            return result if result is not None else "No agents were able to process the request"
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return f"Error processing request: {str(e)}"

# Create a singleton instance
orchestrator = UniversalOrchestrator() 