from duckduckgo_search import DDGS
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from datetime import datetime
from .config import get_model_config
import requests
from bs4 import BeautifulSoup
import re
import logging
current_date = datetime.now().strftime("%Y-%m")

model = get_model_config()
logger = logging.getLogger(__name__)
# 1. Create Tools

@function_tool
def search_duckduckgo(topic):
    """Search for information using DuckDuckGo."""
    print(f"Running DuckDuckGo search for {topic}...")
    
    ddg_api = DDGS()
    results = ddg_api.text(f"{topic} {current_date}", max_results=5)
    if results:
        news_results = "\n\n".join([f"Title: {result['title']}\nURL: {result['href']}\nDescription: {result['body']}" for result in results])
        return news_results
    else:
        return f"Could not find results for {topic}."

@function_tool
def fetch_and_parse_html(url):
    """Fetch HTML content from a URL and return only the body content."""
    logger.info(f"Fetching HTML content from {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()
            
        # Get body content
        body = soup.body
        if body is None:
            return "No body content found in the HTML"
            
        # Get text content
        text = body.get_text(separator='\n', strip=True)
        
        # Clean up excessive newlines and spaces
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

@function_tool
def analyze_content_type(content):
    """Analyze content to determine if it's primarily about products/prices or news."""
    return content

# 2. Create Editor Agents for content processing

editor_agent_price = Agent(
    name="Editor Product Assistant",
    instructions="""Compile and format the search results and price information into a clear report.
    For each product:
    1. Show the product name and description
    2. List all found prices
    3. ALWAYS include the source URL at the beginning of each product section
    4. Highlight any notable price differences or special offers
    5. Format everything in a clear, easy-to-read structure
    
    Format each section like this:
    
    ## [Product Name]
    Source: [URL]
    Description: [Product Description]
    Price: [Price Information]
    [Additional Details]
    """,
    model=model
)

editor_agent_news = Agent(
    name="Editor News Assistant",
    instructions="""Rewrite and give me a news article ready for publishing. 
    For each news story:
    1. ALWAYS start with the source URL
    2. Include a clear headline
    3. Provide the main content
    4. Format in clear sections
    
    Format each section like this:
    
    ## [Headline]
    Source: [URL]
    [News Content]
    """,
    model=model
)

# 3. Create Main Orchestrator Agent

orchestrator_agent = Agent(
    name="Content Orchestrator",
    instructions="""You are the main orchestrator that controls the entire workflow. Your responsibilities include:

    1. Initial Analysis:
       - Analyze the user's query to determine if it needs product/price information or news
       - Decide if a search is necessary based on the context
       - Plan the appropriate steps to fulfill the request

    2. Search and Content Gathering:
       - Use the search_duckduckgo tool when needed to find relevant information
       - Use fetch_and_parse_html to get detailed content from URLs
       - ALWAYS preserve the source URLs throughout the process
       - Extract relevant information from the content

    3. Content Processing:
       - Analyze gathered content to determine its nature
       - Choose the appropriate editor agent based on content type:
         * Hand off to editor_agent_price for:
           - Product listings
           - Price information ($XX.XX format)
           - Product specifications
           - Availability information
           - Shopping-related content
         * Hand off to editor_agent_news for:
           - News articles
           - Press releases
           - General information
           - Industry updates
           - Blog posts
       - Ensure each section includes its source URL

    4. Quality Control:
       - Ensure all gathered information is relevant to the user's query
       - Verify that prices and product information are properly formatted
       - Check that news content is well-organized and clear
       - Verify that EVERY section includes its source URL
       - Handle any errors or missing information appropriately

    IMPORTANT: The final output MUST ALWAYS include source URLs for each piece of information.
    Always maintain context and ensure the final output matches the user's intent.
    """,
    tools=[search_duckduckgo, fetch_and_parse_html],
    model=model,
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[editor_agent_price, editor_agent_news]
)

# 4. Main workflow function

async def run_workflow(topic):
    """Run the workflow with the orchestrator as the main controller."""
    print(f"Starting workflow for topic: {topic}")
    
    # Let the orchestrator handle the entire workflow
    orchestrator_response = await Runner.run(
        orchestrator_agent,
        f"""Process this request for information about: {topic}

        1. Determine if we need to search for information
        2. If needed, use search_duckduckgo to find relevant content
        3. For any URLs found, use fetch_and_parse_html to get detailed content
        4. Analyze the content and hand off to the appropriate editor
        5. Return the final formatted result

        IMPORTANT: 
        - Preserve and include source URLs for all information
        - Each section in the final output must start with its source URL
        - Make sure URLs are clearly visible and properly formatted

        Ensure all steps are properly executed and handle any errors appropriately.
        """
    )
    
    return orchestrator_response.final_output

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_topic = "Davidoff cigars"
    print(f"Running test with topic: {test_topic}")
    print(run_workflow(test_topic))