import logging
from typing import Dict, Any
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from config import get_model_config, TEMPERATURE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
model = get_model_config()

@function_tool
async def explain_concept(query: str) -> Dict[str, Any]:
    """Explain a concept or piece of information in detail.
    
    Args:
        query (str): The concept or topic to explain
        
    Returns:
        Dict containing the explanation and any relevant examples
    """
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
            
            Always aim to make explanations:
            - Accurate and factual
            - Easy to understand
            - Well-structured
            - Practical and applicable
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
        
        if not response or not response.final_output:
            return {
                'success': False,
                'error': 'Failed to generate explanation'
            }
            
        return {
            'success': True,
            'explanation': response.final_output
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Error generating explanation: {str(e)}"
        }

# Create Main Explanation Agent
explanation_orchestrator = Agent(
    name="Explanation Orchestrator",
    instructions="""You are the main orchestrator for generating explanations.
    Your responsibilities include:
    
    1. Query Analysis:
       - Understand what needs to be explained
       - Identify key concepts and components
       - Determine the appropriate level of detail needed
    
    2. Explanation Generation:
       - Use the explain_concept tool to generate clear explanations
       - Ensure explanations are complete and accurate
       - Add context when necessary
       - Include examples where helpful
    
    3. Quality Control:
       - Verify explanations are clear and understandable
       - Ensure all parts of the query are addressed
       - Check that examples are relevant and helpful
    
    4. Response Formatting:
       - Structure the response logically
       - Use appropriate formatting (headings, lists, etc.)
       - Highlight key points and takeaways
    
    You MUST:
    1. Always use the explain_concept tool for generating explanations
    2. Return explanations in a clear, structured format
    3. Include relevant examples when helpful
    4. Handle errors gracefully with clear error messages
    """,
    model=model,
    tools=[explain_concept]
)

async def run_workflow(request: str) -> str:
    """Run the explanation workflow with the orchestrator as the main controller."""
    logger.info(f"Starting explanation workflow for request: {request}")
    
    try:
        # Log received request
        logger.info("Explanation Agent: Received explanation request")
        logger.info(f"Explanation Agent: Request: {request}")
        
        # Create a new Runner instance and execute the explanation
        response =  await Runner.run_sync(
            explanation_orchestrator,
            request
        )
        
        if not response or not response.final_output:
            logger.error("Explanation Agent: No response received from orchestrator")
            return "Error: No response received from orchestrator"
        
        # Extract the explanation from the response
        output = response.final_output
        
        # Handle dictionary responses
        if isinstance(output, dict):
            if not output.get('success', True):
                error_msg = output.get('error', 'Unknown error occurred')
                logger.error(f"Explanation Agent: {error_msg}")
                return f"Error: {error_msg}"
            
            explanation = output.get('explanation', '')
            if explanation:
                logger.info("Explanation Agent: Successfully generated explanation")
                return explanation
            else:
                logger.error("Explanation Agent: Empty explanation received")
                return "Error: Empty explanation received"
        
        # Handle string responses
        elif isinstance(output, str):
            if output.startswith('Error'):
                logger.error(f"Explanation Agent: {output}")
                return output
            else:
                logger.info("Explanation Agent: Successfully generated explanation")
                return output
        
        else:
            logger.error("Explanation Agent: Invalid response format")
            return "Error: Invalid response format"
            
    except Exception as e:
        logger.error(f"Explanation Agent: Error in explanation workflow - {str(e)}")
        return f"Error" 