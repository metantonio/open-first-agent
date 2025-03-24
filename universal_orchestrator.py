from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from duck_browser_agent.dds_agent import run_workflow as run_browser_workflow
from terraform_agent.terraform_agent import run_workflow as run_terraform_workflow
from dev_env_agent.dev_env_agent import run_workflow as run_dev_env_workflow
from aws_cli_agent.aws_cli_agent import run_workflow as run_aws_cli_workflow
from file_system_agent.file_system_agent import run_workflow as run_file_env_workflow
from terminal_agent.terminal_task_agent import run_workflow as run_terminal_workflow
from code_converter_agent.code_converter_agent import run_workflow as run_code_converter_workflow
from explanation_agent.explanation_agent import run_workflow as run_explanation_workflow
import logging
from config import get_model_config, TEMPERATURE
import os

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
               - Any local system operations (open files with cat command, run commands)
               
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

               Code Converter Agent:
               - Converting SAS code to Python code
               - Handling DATA steps conversion to pandas
               - Converting PROC steps to Python equivalents
               - Converting SAS macros to Python functions
               - Maintaining code structure and dependencies
               - Ensuring proper import statements

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

               - Code Conversion Tasks:
                 1. Terminal Agent (open sas files with cat command if needed)
                 2. Code Converter Agent (convert SAS to Python)
                 3. Terminal Agent (save converted files to python files)
                 4. Dev Env Agent (setup Python environment if needed)

            IMPORTANT:
            - Always validate inputs before passing to agents
            - Maintain state across multi-agent workflows
            - Provide clear error messages
            - Ensure proper handoff between agents
            """,
            model=model,
            model_settings=ModelSettings(temperature=TEMPERATURE)
        )

    async def analyze_workflow(self, request: str) -> list:
        """Analyze request to determine required agents and sequence."""
        workflow_response = await Runner.run(
            self.orchestrator_agent,
            f"""Analyze the following request and determine which agents are needed and in what order.
            
            Request: {request}

            Agent Selection Rules:
            1. For code conversion tasks (keywords: convert, sas, to python, .sas):
               - Use "terminal" first to find and read the requested file with cat command, don't use it for other tasks
               - Then "code_converter" to convert the code to requested language
               - Then "terminal" again to save the script file in the requested script language
            
            2. For web tasks (keywords: search, lookup, find online, find):
               - Use "browser" for web searches
               - May be followed by other agents
            
            3. For infrastructure tasks (keywords: terraform, aws, infrastructure):
               - Use "terraform" for IaC tasks
               - Use "aws_cli" for AWS operations
               - May be followed by other agents
            
            4. For development setup (keywords: setup, install, configure):
               - Use "dev_env" for environment setup
               - May be preceded by "browser" for research
            
            5. For file operations (keywords: file, directory, create, delete, find, list):
               - Use "terminal" for file system operations
               - May be followed by other agents

            6. For chat tasks or explanations (keywords: chat, conversation, ask, question):
               - Use "explanation_agent" for explaining the results
               - May be preceded by "browser" for research
               - May be followed by other agents
            
            Return ONLY a comma-separated list of required agents in execution order.
            Example responses:
            - terminal (for single agent)
            - browser (for web research)
            - browser,terminal (for multi-agent sequence)
            - terminal,code_converter,terminal (for code conversion tasks)
            - browser,explanation_agent (for research and explanation)
            """,
            context={"request": request}
        )
        
        # Clean and parse the workflow sequence
        response_text = workflow_response.final_output.strip().lower()
        # Remove any quotes
        response_text = response_text.replace('"', '').replace("'", '')
        logger.info(f"Raw response from orchestrator: {response_text}")
        
        # Split by comma and clean each agent name
        agent_sequence = [agent.strip() for agent in response_text.split(',')]
        logger.info(f"Parsed agent sequence: {agent_sequence}")
        
        # Validate agent types
        valid_agents = {'browser', 'terraform', 'dev_env', 'aws_cli', 'terminal', 'code_converter', 'explanation_agent'}
        agent_sequence = [agent for agent in agent_sequence if agent in valid_agents]
        
        # Special case: If the request involves SAS to Python conversion
        if any(keyword in request.lower() for keyword in ['convert', '.sas', 'sas to python']):
            if agent_sequence != ['terminal', 'code_converter', 'terminal']:
                logger.info("Detected code conversion task, enforcing correct agent sequence")
                agent_sequence = ['terminal', 'code_converter', 'terminal']
        
        # Special case: If the request is clearly a web search
        web_search_keywords = ['search', 'buscar', 'find online', 'look up', 'google', 'web']
        if any(keyword in request.lower() for keyword in web_search_keywords):
            logger.info("Detected web search request, ensuring browser agent is first")
            if 'browser' not in agent_sequence:
                agent_sequence = ['browser'] + agent_sequence
        
        # Default to explanation_agent if no valid agents
        if not agent_sequence:
            logger.warning(f"No valid agents in sequence, defaulting to explanation_agent")
            return ['explanation_agent']
            
        logger.info(f"Final agent sequence: {agent_sequence} for request: {request}")
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
            sas_content = None
            python_code = None
            
            # Special handling for code conversion workflow
            if agent_sequence == ['terminal', 'code_converter', 'terminal']:
                logger.info("Executing code conversion workflow")
                
                # Extract file paths from request
                sas_file = None
                python_file = None
                
                # Look for .sas file in the request
                words = request.lower().split()
                for i, word in enumerate(words):
                    if '.sas' in word:
                        sas_file = word
                        # Look for .py file after the .sas file
                        for next_word in words[i+1:]:
                            if '.py' in next_word:
                                python_file = next_word
                                break
                        break
                
                if not sas_file:
                    return "Error: No .sas file specified in the request"
                
                if not python_file:
                    # Default to same name with .py extension
                    python_file = sas_file.replace('.sas', '.py')
                
                logger.info(f"Processing conversion from {sas_file} to {python_file}")
                
                # Step 1: Read SAS file
                logger.info(f"Step 1: Reading SAS file from {sas_file}")
                try:
                    # The code converter will handle the path resolution
                    sas_content = sas_file
                except Exception as e:
                    logger.error(f"Failed to read SAS file: {str(e)}")
                    return f"Error: Failed to read SAS file - {str(e)}"
                
                # Step 2: Convert code
                if sas_content:
                    logger.info("Step 2: Converting SAS to Python")
                    python_code = run_code_converter_workflow(sas_content)
                    
                    if isinstance(python_code, str) and python_code.startswith('Error'):
                        logger.error(f"Failed to convert code: {python_code}")
                        return python_code
                    
                    logger.info(f"Successfully converted code. Python code length: {len(str(python_code))} characters")
                    logger.info("First 100 characters of Python code: " + str(python_code)[:100] + "...")
                
                # Step 3: Save Python file
                if python_code:
                    logger.info(f"Step 3: Saving Python code to {python_file}")
                    
                    # Ensure output directory exists
                    os.makedirs('output', exist_ok=True)
                    
                    # Properly escape the Python code for the echo command
                    escaped_code = python_code.replace("'", "'\\''")
                    save_request = f"echo '{escaped_code}' > output/{python_file}"
                    
                    result = run_terminal_workflow(save_request)
                    result = result + run_explanation_workflow(f"Print the full code and explain it, suggest improvements: {python_code}")
                    if isinstance(result, str) and result.startswith('Error'):
                        logger.error(f"Failed to save Python file: {result}")
                    else:
                        logger.info(f"Successfully saved Python code to {python_file}")
                    
                    return result
                    
            else:
                # Normal workflow for non-code-conversion tasks
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
                    elif agent_type == "code_converter":
                        result = run_code_converter_workflow(request)
                    elif agent_type == "explanation_agent":
                        result = run_explanation_workflow(request)
                    
                    # Update request with result for context if needed
                    if isinstance(result, dict) and result.get('context'):
                        request = f"{request}\nContext: {result['context']}"
            
            return result if result is not None else "No agents were able to process the request"
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return f"Error processing request: {str(e)}"

# Create a singleton instance
orchestrator = UniversalOrchestrator() 