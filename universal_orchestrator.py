from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from duck_browser_agent.dds_agent import run_workflow as run_browser_workflow
from terraform_agent.terraform_agent import run_workflow as run_terraform_workflow
from dev_env_agent.dev_env_agent import run_workflow as run_dev_env_workflow
from aws_cli_agent.aws_cli_agent import run_workflow as run_aws_cli_workflow
from file_system_agent.file_system_agent import run_workflow as run_file_env_workflow # deprecated, now using mpc
from openai_mcp.main import run_workflow as run_file_system_mpc
from terminal_agent.terminal_task_agent import run_workflow as run_terminal_workflow
from code_converter_agent.code_converter_agent import run_workflow as run_code_converter_workflow
from explanation_agent.explanation_agent import run_workflow as run_explanation_workflow
from mcp_github.main import run_workflow as run_github_workflow
from mcp_gitlab.main import run_workflow as run_gitlab_workflow
from mcp_sequential_thinking.main import run_workflow as run_sequential_thinking
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
               - Sequential thinking or deep thinking about some problem
               
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

               Github Agent:
               - Read github repositories
               - Perform task in github

               Gitlab Agent:
               - Read gitlab repositories
               - Perform task in gitlab

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
               - Use "file_system" for file system operations
               - May be followed by other agents

            6. For chat tasks or explanations (keywords: chat, conversation, ask, question):
               - Use "explanation_agent" for explaining the results
               - May be preceded by "browser" for research
               - May be followed by other agents

            7. For terminal operations (keywords: sudo, ls, pwd, chmod):
                - Use "terminal"

            8. For github operations (keywords: github)
                - Use "github"

            9. For gitlab operations (keywords: gitlab)
                - Use "gitlab"

            10. For deep thinking or sequential thinking (keywords: think, deep)
                - Use "think"
            
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
        valid_agents = {'browser', 'terraform', 'dev_env', 'aws_cli', 'terminal', 'code_converter', 'explanation_agent', 'file_system', 'gitlab','github', 'think'}
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

            # Check if this is a response to the explanation offer
            if request.lower().strip() == 'yes' and hasattr(self, '_last_converted_code'):
                logger.info("User requested explanation of converted code")
                explanation = run_explanation_workflow(f"Print the full code and explain it, suggest improvements: {self._last_converted_code}")
                # Clear the stored code after providing explanation
                delattr(self, '_last_converted_code')
                return explanation

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
                
                # Look for .sas file in request
                words = request.split()
                for i, word in enumerate(words):
                    if word.endswith('.sas'):
                        sas_file = word
                    elif word.endswith('.py'):
                        python_file = word
                
                if not sas_file:
                    return "Error: No .sas file specified in the request"
                
                if not python_file:
                    # Default to same name with .py extension
                    python_file = sas_file.replace('.sas', '.py')
                
                # Check if file exists in current directory or output directory
                sas_file_path = sas_file
                if not os.path.exists(sas_file):
                    output_path = os.path.join('output', sas_file)
                    if os.path.exists(output_path):
                        sas_file_path = output_path
                    else:
                        return f"Error: SAS file not found in either current directory or output directory: {sas_file}"
                
                logger.info(f"Processing conversion from {sas_file_path} to {python_file}")
                
                # Step 1: Read SAS file
                logger.info("Step 1: Reading SAS file content")
                read_request = f"cat {sas_file_path}"
                sas_content = run_terminal_workflow(read_request)
                
                if isinstance(sas_content, str) and sas_content.startswith('Error'):
                    logger.error(f"Failed to read SAS file: {sas_content}")
                    return sas_content
                
                # Step 2: Convert code
                if isinstance(sas_content, str):
                    logger.info("Step 2: Converting SAS to Python: sas_content: " + sas_content)
                    try:
                        # Pass the actual SAS content to the converter
                        python_code = run_code_converter_workflow(sas_content)
                        
                        if isinstance(python_code, str):
                            if python_code.startswith('Error'):
                                logger.error(f"Failed to convert code: {python_code}")
                                return python_code
                            
                            # Step 3: Save Python file
                            logger.info(f"Step 3: Saving Python code to {python_file}")
                            
                            # Ensure output directory exists
                            os.makedirs('output', exist_ok=True)
                            
                            # Write the file directly
                            output_path = os.path.join('output', python_file)
                            try:
                                with open(output_path, 'w', encoding='utf-8') as f:
                                    f.write(python_code)
                                logger.info(f"Successfully saved Python code to {output_path}")
                                
                                # Store the code for potential explanation
                                self._last_converted_code = python_code
                                # Return success message with option to get explanation
                                return f"""Successfully converted and saved the code to output/{python_file}

The conversion has been completed. Would you like me to explain the converted code and suggest possible improvements? (Please respond with 'yes' if you'd like an explanation)"""
                            except Exception as e:
                                error_msg = f"Failed to save Python file: {str(e)}"
                                logger.error(error_msg)
                                return f"Error: {error_msg}"
                        else:
                            logger.error("Invalid Python code format returned from converter")
                            return "Error: Invalid Python code format returned from converter"
                    except Exception as e:
                        error_msg = f"Error during code conversion: {str(e)}"
                        logger.error(error_msg)
                        return f"Error: {error_msg}"
                else:
                    logger.error("Invalid SAS content format")
                    return "Error: Invalid SAS content format"

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
                    elif agent_type == 'file_system':
                        result = await run_file_system_mpc(request)
                    elif agent_type == "github":
                        result = await run_github_workflow(request)
                    elif agent_type == "gitlab":
                        result == await run_gitlab_workflow(request)
                    elif agent_type == "think":
                        result == await run_sequential_thinking(request)
                    
                    # Update request with result for context if needed
                    if isinstance(result, dict) and result.get('context'):
                        request = f"{request}\nContext: {result['context']}"
            
            return result if result is not None else "No agents were able to process the request"
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return f"Error processing request: {str(e)}"

# Create a singleton instance
orchestrator = UniversalOrchestrator() 