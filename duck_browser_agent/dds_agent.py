from duckduckgo_search import DDGS
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from datetime import datetime
from .config import get_model_config
import requests
from bs4 import BeautifulSoup
import re

current_date = datetime.now().strftime("%Y-%m")

model = get_model_config()

# 1. Create Tools

@function_tool
def get_news_articles(topic):
    print(f"Running DuckDuckGo news search for {topic}...")
    
    # DuckDuckGo search
    ddg_api = DDGS()
    results = ddg_api.text(f"{topic} {current_date}", max_results=5)
    if results:
        news_results = "\n\n".join([f"Title: {result['title']}\nURL: {result['href']}\nDescription: {result['body']}" for result in results])
        print(news_results)
        return news_results
    else:
        return f"Could not find results for {topic}."

@function_tool
def fetch_and_parse_html(url):
    """Fetch HTML content from a URL and return it for parsing."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

@function_tool
def analyze_content_type(content):
    """Analyze content to determine if it's primarily about products/prices or news."""
    return content

# 2. Create AI Agents

search_agent = Agent(
    name="Search Assistant",
    instructions="You search for products and their prices using DuckDuckGo search.",
    tools=[get_news_articles],
    model=model
)

html_parser_agent = Agent(
    name="HTML Parser",
    instructions="""You are an expert at analyzing HTML content to find product information and prices.
    When given HTML content:
    1. Look for price information in common formats ($XX.XX, $XXX.XX, etc.)
    2. Look for product titles, descriptions, and specifications
    3. Extract any relevant availability information
    4. Format the information in a clear, structured way
    5. If you can't find price information, indicate that clearly
    """,
    tools=[fetch_and_parse_html],
    model=model
)

editor_agent_price = Agent(
    name="Editor Product Assistant",
    instructions="""Compile and format the search results and price information into a clear report.
    For each product:
    1. Show the product name and description
    2. List all found prices
    3. Include the source URLs
    4. Highlight any notable price differences or special offers
    5. Format everything in a clear, easy-to-read structure
    """,
    model=model
)

editor_agent_news = Agent(
    name="Editor News Assistant",
    instructions="Rewrite and give me a news article ready for publishing. Each News story in separate section.",
    model=model
)

orchestrator_agent = Agent(
    name="Content Orchestrator",
    instructions="""You are the orchestrator that coordinates the workflow between different agents.
    Your main responsibilities are:
    1. Analyze the search results and determine their primary nature (product/price information vs news)
    2. Choose the appropriate editor agent based on the content:
       - Hand off to editor_agent_price for content containing:
         * Product listings
         * Price information ($XX.XX format)
         * Product specifications
         * Availability information
         * Shopping-related content
       - Hand off to editor_agent_news for content containing:
         * News articles
         * Press releases
         * General information
         * Industry updates
         * Blog posts
    3. Ensure the final output matches the user's intent
    4. Handle any errors or edge cases appropriately
    
    For each piece of content, analyze:
    - Presence of price patterns ($XX.XX)
    - Product-specific terminology (price, cost, available, in stock)
    - News-related content markers (article, report, announcement)
    
    Then hand off to the appropriate editor agent for final formatting.
    """,
    model=model,
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[editor_agent_price, editor_agent_news]
)

# 3. Create workflow

def run_news_workflow(topic):
    print(f"Running search workflow for {topic}...")
    
    # Step 1: Search for products
    search_response = Runner.run_sync(
        search_agent,
        f"Find information about {topic}"
    )
    raw_results = search_response.final_output
    
    # Step 2: Parse URLs and extract information
    urls = re.findall(r'URL: (https?://[^\s]+)', raw_results)
    detailed_info = []
    
    for url in urls:
        print(f"Parsing URL: {url}")
        html_content = fetch_and_parse_html(url)
        
        parse_response = Runner.run_sync(
            html_parser_agent,
            f"Analyze this HTML content and extract relevant information: {html_content[:50000]}"
        )
        detailed_info.append(f"Source: {url}\n{parse_response.final_output}")
    
    # Combine all information
    combined_info = f"Search Results:\n{raw_results}\n\nDetailed Information:\n" + "\n\n".join(detailed_info)
    
    # Step 3: Let orchestrator analyze and hand off to appropriate editor
    orchestrator_response = Runner.run_sync(
        orchestrator_agent,
        f"""Analyze this content and hand off to the appropriate editor agent.
        The content contains product information, prices, and/or news articles.
        Choose the most appropriate editor based on the content type.
        
        Content to analyze:
        {combined_info}
        """
    )
    
    edited_content = orchestrator_response.final_output
    
    print("Final report:")
    print(edited_content)
    
    return edited_content

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_topic = "Davidoff cigars"
    print(f"Running test with topic: {test_topic}")
    print(run_news_workflow(test_topic))