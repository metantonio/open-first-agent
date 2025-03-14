from duckduckgo_search import DDGS
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool
from datetime import datetime
from .config import get_model_config

current_date = datetime.now().strftime("%Y-%m")

model = get_model_config()

# 1. Create Internet Search Tool

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
        return f"Could not find news results for {topic}."
    
# 2. Create AI Agents

# News Agent to fetch news
duck_browser_agent = Agent(
    name="News Assistant",
    instructions="You provide the latest news articles for a given topic using DuckDuckGo search.",
    tools=[get_news_articles],
    model=model
)

# Editor Agent to edit news
editor_agent = Agent(
    name="Editor Assistant",
    instructions="Rewrite and give me as news article ready for publishing. Each News story in separate section.",
    model=model
)

# 3. Create workflow

def run_news_workflow(topic):
    print("Running news Agent workflow...")
    
    # Step 1: Fetch news
    news_response = Runner.run_sync(
        duck_browser_agent,
        f"Get me the news about {topic} on {current_date}"
    )
    
    # Access the content from RunResult object
    raw_news = news_response.final_output
    
    # Step 2: Pass news to editor for final review
    edited_news_response = Runner.run_sync(
        editor_agent,
        raw_news
    )
    
    # Access the content from RunResult object
    edited_news = edited_news_response.final_output
    
    print("Final news article:")
    print(edited_news)
    
    return edited_news

# Example of running the news workflow for a given topic
print(run_news_workflow("AI"))