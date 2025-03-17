import chainlit as cl
from universal_orchestrator import orchestrator
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('agent.log')
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(ch)

@cl.on_message
async def main(message: cl.Message):
    """
    Main function to handle user messages and route them to appropriate agents.
    """
    # Get the user request
    request = message.content
    
    # Send a thinking message and show a loading indicator
    msg = cl.Message(
        content=f"🤔 Processing your request: '{request}'...\nThis may take a few moments.",
        author="AI Assistant"
    )
    await msg.send()
    
    try:
        # Process the request using the universal orchestrator
        response = await orchestrator.process_request(request)
        
        # Update the message with the results
        await cl.Message(
            content=f"✅ Here's what I found:\n\n{response}",
            author="AI Assistant"
        ).send()
    except Exception as e:
        # Handle any errors
        error_message = f"❌ Sorry, I encountered an error: {str(e)}"
        if "429" in str(e):
            error_message += "\nIt seems we've hit an API rate limit. Please try again in a few minutes."
        await cl.Message(
            content=error_message,
            author="AI Assistant"
        ).send()

@cl.on_chat_start
async def start():
    """
    Function that runs when a new chat session starts.
    """
    # Send a welcome message
    await cl.Message(
        content="""👋 Welcome to the AI Assistant!

I can help you with various tasks:

1. 🌐 Web Search and News:
   - Find and summarize news articles
   - Search for information on any topic
   - Process and analyze web content

2. 🏗️ Terraform Infrastructure:
   - Create and manage Terraform configurations
   - Analyze existing Terraform files
   - Execute Terraform operations
   - Get infrastructure recommendations

Simply type your request, and I'll automatically determine the best way to help you!

What would you like to do?""",
        author="AI Assistant"
    ).send() 