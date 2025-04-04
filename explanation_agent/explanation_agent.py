import logging
from typing import Dict, Any
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from config import get_model_config, TEMPERATURE
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
model = get_model_config()

@function_tool
async def explain_concept(query: str) -> Dict[str, Any]:
    """Explain a concept or piece of information in detail."""
    try:
        # Create an agent specifically for generating explanations
        explanation_generator = Agent(
            name="Concept Explainer",
            instructions="""You are an expert at explaining complex concepts clearly and concisely.
            Your task is to:
            1. Break down complex topics into understandable parts
            2. Use clear, simple language
            3. Provide relevant examples when helpful
            4. Structure explanations logically
            5. Highlight key points and takeaways
            
            Format your responses with:
            - Clear headings for different aspects
            - Bullet points for lists
            - Code examples if relevant
            - Analogies when helpful
            """,
            model=model,
            model_settings=ModelSettings(temperature=TEMPERATURE)
        )
        
        # Generate the explanation
        response = await Runner.run(
            explanation_generator,
            f"Please explain the following concept: {query}",
            context={"query": query}
        )
        
        return {
            'success': bool(response and response.final_output),
            'explanation': response.final_output if response else None,
            'error': None if response and response.final_output else 'Failed to generate explanation'
        }
        
    except Exception as e:
        logger.error(f"Error in explain_concept: {str(e)}")
        return {
            'success': False,
            'explanation': None,
            'error': f"Error generating explanation: {str(e)}"
        }

# Create Main Explanation Agent
explanation_orchestrator = Agent(
    name="Explanation Orchestrator",
    instructions="""You are the main orchestrator for generating explanations.
    Your responsibilities include:
    1. Query Analysis
    2. Explanation Generation
    3. Quality Control
    4. Response Formatting
    """,
    model=model,
    tools=[explain_concept]
)

async def run_workflow(request: str) -> str:
    """Run the explanation workflow with proper async handling."""
    logger.info(f"Starting explanation workflow for request: {request}")
    
    try:
        # Create a new Runner instance and execute the explanation
        response = await Runner.run(
            explanation_orchestrator,
            request
        )
        
        if not response or not response.final_output:
            logger.error("No response received from orchestrator")
            return "Error: No response received from orchestrator"
        
        output = response.final_output
        
        # Handle different response formats
        if isinstance(output, dict):
            if output.get('success'):
                return output.get('explanation', 'Explanation generated but empty')
            return output.get('error', 'Unknown error occurred')
        
        return str(output)
            
    except Exception as e:
        logger.error(f"Error in explanation workflow: {str(e)}")
        return f"Error: {str(e)}"

def run_workflow_sync(request: str) -> str:
    """Synchronous wrapper for the async workflow."""
    try:
        return asyncio.get_event_loop().run_until_complete(run_workflow(request))
    except RuntimeError as e:
        if "no running event loop" in str(e):
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(run_workflow(request))
            finally:
                loop.close()
        raise