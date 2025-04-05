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
from prompts.universal_orchestrator_prompt import universal_orchestrator_prompt
import logging
from config import get_model_config, TEMPERATURE
import os
from typing import Set
import sys
from logger import logger

model = get_model_config()

""" logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.addHandler(logging.FileHandler('agent.log')) """

class UniversalOrchestrator:
    def __init__(self):
        self.orchestrator_agent = Agent(
            name="Universal Orchestrator",
            instructions=universal_orchestrator_prompt,
            model=model,
            model_settings=ModelSettings(temperature=TEMPERATURE)
        )
        self._browser_enabled = True  # Default to enabled

    @property
    def browser_enabled(self) -> bool:
        return self._browser_enabled
    
    @browser_enabled.setter
    def browser_enabled(self, value: bool):
        self._browser_enabled = value
        logger.info(f"Browser agent {'enabled' if value else 'disabled'}")

    def get_valid_agents(self) -> Set[str]:
        """Get the current set of valid agents based on settings"""
        base_agents = {'terraform', 'dev_env', 'aws_cli', 'terminal', 
                      'code_converter', 'explanation_agent', 'file_system', 
                      'gitlab', 'github', 'think'}
        if self._browser_enabled:
            base_agents.add('browser')
        return base_agents

    async def analyze_workflow(self, request: str) -> list:
        """Analyze request to determine required agents and sequence."""
        workflow_response = await Runner.run(
            self.orchestrator_agent,
            f"""Analyze the following request and determine which agents are needed and in what order.
            
            Request: {request}

            Agent Selection Rules:
            1. For code conversion tasks (keywords: sas to python, transform to):
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
        valid_agents = self.get_valid_agents()
        agent_sequence = [agent for agent in agent_sequence if agent in valid_agents]
        
        # Special case: If the request involves SAS to Python conversion
        if any(keyword in request.lower() for keyword in ['.sas']):
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
            cleaned_request = request.lower().strip()
            if cleaned_request == 'yes':
                logger.info(f"Checking for explanation request, has _last_converted_code: {hasattr(self, '_last_converted_code')}")
                if hasattr(self, '_last_converted_code'):
                    logger.info(f"User requested explanation of converted code. Code length: {len(self._last_converted_code)}")
                    try:
                        explanation = await run_explanation_workflow(
                            f"Print the full code first and then explain it, finally suggest improvements: {self._last_converted_code}"
                        )
                        logger.info("Explanation generated successfully")
                        try:
                            # Clear the stored code after providing explanation
                            delattr(self, '_last_converted_code')
                        except Exception as converted_error:
                            logger.error(f"Error deleting latest converted code: {str(converted_error)}")
                        logger.info(f"explanation \n: {explanation}")    
                        return explanation
                    except Exception as e:
                        logger.error(f"Error generating explanation: {str(e)}", exc_info=True)
                        return f"Error generating explanation: {str(e)}"
                else:
                    logger.warning("User requested explanation but no converted code was found")
                    return "No converted code available for explanation. Please perform a code conversion first."

            # Analyze workflow to get agent sequence
            agent_sequence = await self.analyze_workflow(request)
            logger.info(f"Processing request with agent sequence: {agent_sequence}")
            
            # Execute agents in sequence
            result = None
            
            # Special handling for code conversion workflow
            if agent_sequence == ['terminal', 'code_converter', 'terminal']:
                logger.info("Executing code conversion workflow")
                try:
                    result = await self._handle_code_conversion(request)
                    return result
                except Exception as e:
                    logger.error(f"Error in code conversion workflow: {str(e)}")
                    return f"Error during code conversion: {str(e)}"
            
            # Normal workflow for non-code-conversion tasks
            for agent_type in agent_sequence:
                logger.info(f"Executing agent: {agent_type}")
                
                try:
                    if agent_type == "browser":
                        result = await run_browser_workflow(request)
                    elif agent_type == "terraform":
                        result = await run_terraform_workflow(request)
                    elif agent_type == "dev_env":
                        result = await run_dev_env_workflow(request)
                    elif agent_type == "aws_cli":
                        result = await run_aws_cli_workflow(request)
                    elif agent_type == "terminal":
                        result = await run_terminal_workflow(request)
                    elif agent_type == "code_converter":
                        result = await run_code_converter_workflow(request)
                    elif agent_type == "explanation_agent":
                        result = await run_explanation_workflow(request)
                    elif agent_type == 'file_system':
                        result = await run_file_system_mpc(request)
                    elif agent_type == "github":
                        result = await run_github_workflow(request)
                    elif agent_type == "gitlab":
                        result = await run_gitlab_workflow(request)
                    elif agent_type == "think":
                        result = await run_sequential_thinking(request)
                    
                    # Update request with result for context if needed
                    if isinstance(result, dict) and result.get('context'):
                        request = f"{request}\nContext: {result['context']}"
                        
                except Exception as e:
                    logger.error(f"Error executing agent {agent_type}: {str(e)}")
                    return f"Error in {agent_type} agent: {str(e)}"

            return result if result is not None else "No agents were able to process the request"
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return f"Error processing request: {str(e)}"

    async def _handle_code_conversion(self, request: str):
        """Handle the code conversion workflow with proper async operations"""
        try:
            # Extract file paths from request
            sas_file = None
            python_file = None
            
            # Look for .sas file in request
            words = request.split()
            for word in words:
                if word.endswith('.sas'):
                    sas_file = word
                elif word.endswith('.py'):
                    python_file = word
            
            if not sas_file:
                return "Error: No .sas file specified in the request"
            
            if not python_file:
                python_file = sas_file.replace('.sas', '.py')
            
            # Check file existence
            sas_file_path = sas_file
            if not os.path.exists(sas_file):
                output_path = os.path.join('output', sas_file)
                if os.path.exists(output_path):
                    sas_file_path = output_path
                else:
                    return f"Error: SAS file not found: {sas_file}"
            
            logger.info(f"Converting {sas_file_path} to {python_file}")
            
            try:
                # Step 1: Read SAS file
                read_request = f"cat {sas_file_path}"
                sas_content_response = await run_terminal_workflow(read_request)
                
                # Handle the response properly
                if isinstance(sas_content_response, str) and sas_content_response.startswith('Error'):
                    return sas_content_response
                
                # Step 2: Convert code
                python_code_response = await run_code_converter_workflow(sas_content_response)
                
                if isinstance(python_code_response, str) and python_code_response.startswith('Error'):
                    return python_code_response
                
                # Step 3: Save Python file
                os.makedirs('output', exist_ok=True)
                output_path = os.path.join('output', python_file)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(python_code_response)
                
                self._last_converted_code = python_code_response
                return f"""Successfully converted to output/{python_file}
                
    Would you like an explanation of the converted code? (respond 'yes')"""
                
            except Exception as e:
                error_msg = f"Failed to save Python file: {str(e)}"
                logger.error(error_msg)
                return f"Error: {error_msg}"
                
        except Exception as e:
            logger.error(f"Unexpected error in code conversion: {str(e)}")
            return f"Error: {str(e)}"
# Create a singleton instance
orchestrator = UniversalOrchestrator() 