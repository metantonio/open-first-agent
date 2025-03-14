import chainlit as cl
from duck_browser_agent.dds_agent import run_news_workflow

@cl.on_message
async def main(message: cl.Message):
    """
    Main function to handle user messages and run the news workflow.
    """
    # Get the topic from the user message
    topic = message.content
    
    # Send a thinking message and show a loading indicator
    msg = cl.Message(
        content=f"🔍 Searching for news about '{topic}'...\nThis may take a few moments as I search and process the results.",
        author="News Bot"
    )
    await msg.send()
    
    try:
        # Run the news workflow
        news_content = run_news_workflow(topic)
        
        # Update the message with the results
        await cl.Message(
            content=f"📰 Here are the latest news articles about '{topic}':\n\n{news_content}",
            author="News Bot"
        ).send()
    except Exception as e:
        # Handle any errors
        error_message = f"❌ Sorry, I encountered an error while fetching news: {str(e)}"
        if "429" in str(e):
            error_message += "\nIt seems we've hit the DuckDuckGo rate limit. Please try again in a few minutes."
        await cl.Message(
            content=error_message,
            author="News Bot"
        ).send()

@cl.on_chat_start
async def start():
    """
    Function that runs when a new chat session starts.
    """
    # Send a welcome message
    await cl.Message(
        content="""👋 Welcome to the News Assistant!

I can help you find and summarize the latest news on any topic. Simply type a topic or keyword you're interested in, and I'll:
1. Search for recent news articles
2. Process and summarize the findings
3. Present them in an easy-to-read format

What topic would you like to get news about?""",
        author="News Bot"
    ).send() 