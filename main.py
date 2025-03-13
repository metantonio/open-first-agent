import asyncio
import json
import csv
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from agents import Agent, Runner, function_tool, AsyncOpenAI, OpenAIChatCompletionsModel, ModelSettings

# External LLM provider (uncommentif you are goind to use Ollama, LLMStudio)
external_provider = AsyncOpenAI(base_url = "http://localhost:11434/v1")


# Define tools for web scraping
@function_tool
def scrape_mikes_cigars(brand: str) -> list:
    """
    Scrape Mike's Cigars website for products of a specific brand.
    
    Args:
        brand: The cigar brand to search for
    
    Returns:
        List of products with details
    """
    url = f"https://mikescigars.com/catalogsearch/result/?q={brand.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        product_items = soup.select('.product-item')
        for item in product_items[:5]:  # Limit to first 5 products for demonstration
            name_elem = item.select_one('.product-title')
            price_elem = item.select_one('.price')
            
            if name_elem and price_elem:
                name = name_elem.text.strip()
                price = price_elem.text.strip()
                
                products.append({
                    "website": "mikescigars.com",
                    "name": name,
                    "price": price,
                    "url": "https://www.mikescigars.com" + name_elem.get('href', '') if name_elem.get('href') else ""
                })
        
        return products
    except Exception as e:
        return [{"error": f"Failed to scrape Mike's Cigars: {str(e)}"}]

@function_tool
def scrape_cigars_com(brand: str) -> list:
    """
    Scrape Cigars.com website for products of a specific brand.
    
    Args:
        brand: The cigar brand to search for
    
    Returns:
        List of products with details
    """
    url = f"https://www.cigars.com/search/?q={brand.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        product_items = soup.select('.product-card')
        for item in product_items[:5]:  # Limit to first 5 products for demonstration
            name_elem = item.select_one('.product-card__title')
            price_elem = item.select_one('.product-card__price')
            
            if name_elem and price_elem:
                name = name_elem.text.strip()
                price = price_elem.text.strip()
                
                products.append({
                    "website": "cigars.com",
                    "name": name,
                    "price": price,
                    "url": "https://www.cigars.com" + name_elem.get('href', '') if name_elem.get('href') else ""
                })
        
        return products
    except Exception as e:
        return [{"error": f"Failed to scrape Cigars.com: {str(e)}"}]

@function_tool
def compare_products(mikes_products: list, cigars_products: list) -> list:
    """
    Compare products from both websites to find matching items.
    
    Args:
        mikes_products: List of products from Mike's Cigars
        cigars_products: List of products from Cigars.com
    
    Returns:
        List of matching products with comparison data
    """
    matched_products = []
    
    for mikes_product in mikes_products:
        if "error" in mikes_product:
            continue
            
        for cigars_product in cigars_products:
            if "error" in cigars_product:
                continue
                
            # Simple string similarity check - can be improved
            if similar_product_names(mikes_product["name"], cigars_product["name"]):
                matched_products.append({
                    "product_name": mikes_product["name"],
                    "mikes_cigars": {
                        "price": mikes_product["price"],
                        "url": mikes_product["url"]
                    },
                    "cigars_com": {
                        "price": cigars_product["price"],
                        "url": cigars_product["url"]
                    }
                })
                break
    
    return matched_products

@function_tool
def similar_product_names(name1: str, name2: str) -> bool:
    """
    Check if two product names are similar enough to be considered the same product.
    
    Args:
        name1: First product name
        name2: Second product name
    
    Returns:
        Boolean indicating if names are similar
    """
    name1 = name1.lower()
    name2 = name2.lower()
    
    # Split names into words and find common words
    words1 = set(name1.split())
    words2 = set(name2.split())
    common_words = words1.intersection(words2)
    
    # If more than 50% of the words match, consider them similar
    return len(common_words) >= min(len(words1), len(words2)) * 0.5

@function_tool
def save_to_json(comparison_data: list, brand: str) -> str:
    """
    Save comparison data to a JSON file with current date.
    
    Args:
        comparison_data: List of product comparisons
        brand: The brand being compared
    
    Returns:
        Path to the saved JSON file
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_data = {
        "date": current_date,
        "brand": brand,
        "comparisons": comparison_data
    }
    
    filename = f"{brand.replace(' ', '_')}_comparison_{current_date}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    return filename

@function_tool
def convert_json_to_csv(json_file: str) -> str:
    """
    Convert JSON comparison data to CSV format.
    
    Args:
        json_file: Path to the JSON file
    
    Returns:
        Path to the created CSV file
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    csv_filename = json_file.replace('.json', '.csv')
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['Date', 'Brand', 'Product Name', 'Mike\'s Cigars Price', 'Mike\'s Cigars URL', 'Cigars.com Price', 'Cigars.com URL'])
        
        # Write data rows
        for comparison in data['comparisons']:
            writer.writerow([
                data['date'],
                data['brand'],
                comparison['product_name'],
                comparison['mikes_cigars']['price'],
                comparison['mikes_cigars']['url'],
                comparison['cigars_com']['price'],
                comparison['cigars_com']['url']
            ])
    
    return csv_filename

# Define the Scraper Agent
scraper_agent = Agent(
    name="Cigar Scraper Agent",
    instructions="""
    You are a specialized agent for scraping cigar websites. 
    Your task is to search for a specific cigar brand on Mike's Cigars and Cigars.com,
    then compare products with similar presentations across both websites.
    Use the scrape_mikes_cigars and scrape_cigars_com tools to get product information,
    then use the compare_products tool to find matching items.
    """,
    model=OpenAIChatCompletionsModel(
        model="llama3.2",
        openai_client=external_provider,
    ),
    tools=[scrape_mikes_cigars, scrape_cigars_com, compare_products]
)

# Define the JSON Export Agent
json_agent = Agent(
    name="JSON Export Agent",
    instructions="""
    You are a specialized agent for exporting cigar comparison data to JSON format.
    Your task is to take the comparison data from the Scraper Agent and save it to a JSON file,
    making sure to include the current date and the brand being compared.
    Use the save_to_json tool to accomplish this.
    """,
    model=OpenAIChatCompletionsModel(
        model="llama3.2",
        openai_client=external_provider,
    ),
    tools=[save_to_json]
)

# Define the CSV Conversion Agent
csv_agent = Agent(
    name="CSV Conversion Agent",
    instructions="""
    You are a specialized agent for converting data from JSON to CSV format.
    Your task is to take a JSON file containing cigar comparison data and convert it to a CSV table.
    Use the convert_json_to_csv tool to accomplish this.
    """,
    model=OpenAIChatCompletionsModel(
        model="llama3.2",
        openai_client=external_provider,
    ),
    tools=[convert_json_to_csv]
)

# Define the Orchestrator Agent with handoffs to specialized agents
orchestrator_agent = Agent(
    name="Cigar Comparison Orchestrator",
    instructions="""
    You are an orchestrator agent that coordinates the cigar comparison workflow.
    
    1. First, understand the user's request for which cigar brand to compare.
    2. Hand off to the Scraper Agent to scrape and compare products.
    3. Hand off to the JSON Export Agent to save the comparison data.
    4. Hand off to the CSV Conversion Agent to convert the data to CSV format.
    5. Finally, summarize the results to the user.
    
    Be helpful and informative throughout the process.
    """,
    model=OpenAIChatCompletionsModel(
        model="llama3.2",
        openai_client=external_provider,
    ),
    model_settings=ModelSettings(temperature=0.5),
    handoffs=[scraper_agent, json_agent, csv_agent]
)

async def main():
    # Get the brand to search for
    brand = input("Enter the cigar brand to compare: ")
    
    # Run the orchestrator agent
    result = await Runner.run(
        orchestrator_agent, 
        input=f"Compare cigars of the brand '{brand}' between mikescigars.com and cigars.com. Save the results to JSON with today's date, then convert to CSV."
    )
    
    print("\nFinal result:")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())