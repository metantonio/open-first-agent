import asyncio
import json
import csv
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from agents import Agent, Runner, function_tool, AsyncOpenAI, OpenAIChatCompletionsModel, ModelSettings, AsyncOpenAI, WebSearchTool
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cigar_scraper.log')
    ]
)
logger = logging.getLogger(__name__)

# External LLM provider by default with ollama (if you are goind to use Ollama, LLMStudio)
external_provider= {
    "model":"llama3.2",
    "client":AsyncOpenAI(base_url = "http://localhost:11434/v1")
}

# If you are going to use OpenAI use this provider
openai_provider= {
    "model":"gpt-4o",
    "client":AsyncOpenAI()
}

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
    logger.info(f"\n=== Starting Mike's Cigars scrape for brand: {brand} ===")
    url = f"https://mikescigars.com/catalogsearch/result/?q={brand.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        logger.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        # Updated selectors to match Mike's Cigars website structure
        product_items = soup.select('.product-item')
        logger.info(f"Found {len(product_items)} products on Mike's Cigars")
        
        for item in product_items:
            name_elem = item.select_one('.product-item-name')
            price_elem = item.select_one('.price')
            href = item.select_one('a.product-item-photo')
            
            if name_elem and price_elem:
                name = name_elem.text.strip()
                price = price_elem.text.strip()
                url = href.get('href', '') if href else ""
                
                product = {
                    "website": "mikescigars.com",
                    "name": name,
                    "price": price,
                    "url": url
                }
                products.append(product)
                logger.info(f"\nFound product: {name} - {price} - {url}")
        
        logger.info(f"=== Completed Mike's Cigars scrape with {len(products)} products ===\n")
        return products
    except Exception as e:
        logger.error(f"Error scraping Mike's Cigars: {str(e)}")
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
    logger.info(f"\n=== Starting Cigars.com scrape for brand: {brand} ===")
    url = f"https://www.cigars.com/search?lang=en_US&jrSubmitButton=&q={brand.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        logger.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        # Updated selectors to match Cigars.com website structure
        product_items = soup.select('.product-card')
        logger.info(f"Found {len(product_items)} products on Cigars.com")
        
        for item in product_items:
            name_elem = item.select_one('.brand-name')
            price_elem = item.select_one('.prices')
            href = item.select_one('a')
            
            if name_elem and price_elem:
                name = name_elem.text.strip()
                price = price_elem.text.strip()
                url = "https://www.cigars.com" + href.get('href', '') if href else ""
                
                product = {
                    "website": "cigars.com",
                    "name": name,
                    "price": price,
                    "url": url
                }
                products.append(product)
                logger.info(f"\nFound product: {name} - {price} - {url}")
        
        logger.info(f"=== Completed Cigars.com scrape with {len(products)} products ===\n")
        return products
    except Exception as e:
        logger.error(f"Error scraping Cigars.com: {str(e)}")
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
    logger.info("\n=== Starting product comparison ===")
    matched_products = []
    
    logger.info(f"Comparing {len(mikes_products)} Mike's Cigars products with {len(cigars_products)} Cigars.com products")
    
    for mikes_product in mikes_products:
        if "error" in mikes_product:
            logger.info(f"Skipping Mike's Cigars product due to error: {mikes_product['error']}")
            continue
            
        for cigars_product in cigars_products:
            if "error" in cigars_product:
                logger.info(f"Skipping Cigars.com product due to error: {cigars_product['error']}")
                continue
                
            if similar_product_names(mikes_product["name"], cigars_product["name"]):
                match = {
                    "product_name": mikes_product["name"],
                    "mikes_cigars": {
                        "price": mikes_product["price"],
                        "url": mikes_product["url"]
                    },
                    "cigars_com": {
                        "price": cigars_product["price"],
                        "url": cigars_product["url"]
                    }
                }
                matched_products.append(match)
                logger.info(f"\nFound matching product: {mikes_product['name']}")
                logger.info(f"Mike's Cigars: {mikes_product['price']}")
                logger.info(f"Cigars.com: {cigars_product['price']}")
    
    logger.info(f"=== Completed comparison with {len(matched_products)} matches ===\n")
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
    
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(current_dir, f"{brand.replace(' ', '_')}_comparison_{current_date}.json")
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"JSON file created successfully at: {filename}")
    except Exception as e:
        logger.error(f"Error creating JSON file: {str(e)}")
        raise
    
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
    try:
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
        
        logger.info(f"CSV file created successfully at: {csv_filename}")
        return csv_filename
    except Exception as e:
        logger.error(f"Error creating CSV file: {str(e)}")
        raise

@function_tool
def save_all_products(mikes_products: list, cigars_products: list, brand: str) -> dict:
    """
    Save all scraped products from both websites, regardless of matches.
    
    Args:
        mikes_products: List of products from Mike's Cigars
        cigars_products: List of products from Cigars.com
        brand: The brand being searched
    
    Returns:
        Dictionary with all products and metadata
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_dir = os.getcwd()
    
    # Filter out error entries
    mikes_products = [p for p in mikes_products if "error" not in p]
    cigars_products = [p for p in cigars_products if "error" not in p]
    
    all_products_data = {
        "date": current_date,
        "brand": brand,
        "mikes_cigars_products": mikes_products,
        "cigars_com_products": cigars_products
    }
    
    # Save to JSON
    json_filename = os.path.join(current_dir, f"{brand.replace(' ', '_')}_all_products_{current_date}.json")
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(all_products_data, f, indent=2)
        logger.info(f"All products JSON file created successfully at: {json_filename}")
    except Exception as e:
        logger.error(f"Error creating all products JSON file: {str(e)}")
        raise
    
    # Save to CSV
    csv_filename = json_filename.replace('.json', '.csv')
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Date', 'Brand', 'Website', 'Product Name', 'Price', 'URL'])
            
            # Write Mike's Cigars products
            for product in mikes_products:
                writer.writerow([
                    current_date,
                    brand,
                    'mikescigars.com',
                    product.get('name', 'Unknown'),
                    product.get('price', 'N/A'),
                    product.get('url', 'N/A')
                ])
            
            # Write Cigars.com products
            for product in cigars_products:
                writer.writerow([
                    current_date,
                    brand,
                    'cigars.com',
                    product.get('name', 'Unknown'),
                    product.get('price', 'N/A'),
                    product.get('url', 'N/A')
                ])
        
        logger.info(f"All products CSV file created successfully at: {csv_filename}")
    except Exception as e:
        logger.error(f"Error creating all products CSV file: {str(e)}")
        raise
    
    return {
        "json_file": json_filename,
        "csv_file": csv_filename,
        "data": all_products_data
    }

# Define the Scraper Agent
scraper_agent = Agent(
    name="Cigar Scraper Agent",
    instructions="""
    You are a specialized agent for scraping cigar websites. 
    Your task is to search for a specific cigar brand on Mike's Cigars and Cigars.com,
    and collect all product information.

    1. First use scrape_mikes_cigars to get products from Mike's Cigars
    2. Then use scrape_cigars_com to get products from Cigars.com
    3. Finally use compare_products to find matching items

    Return the results in this exact format:
    {
        "mikes_products": [list of products from Mike's Cigars],
        "cigars_products": [list of products from Cigars.com],
        "matches": [list of matching products]
    }
    """,
    model=OpenAIChatCompletionsModel(
        model=external_provider["model"],
        openai_client=external_provider["client"],
    ),
    tools=[scrape_mikes_cigars, scrape_cigars_com, compare_products],
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
        model=external_provider["model"],
        openai_client=external_provider["client"],
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
        model=external_provider["model"],
        openai_client=external_provider["client"],
    ),
    tools=[convert_json_to_csv]
)

# Define the All Products Export Agent
all_products_agent = Agent(
    name="All Products Export Agent",
    instructions="""
    You are a specialized agent for saving all scraped cigar products.
    Your task is to take all products from both Mike's Cigars and Cigars.com,
    regardless of whether they match or not, and save them to both JSON and CSV formats.
    
    Use the save_all_products tool to save all products from both websites.
    The tool will automatically create both JSON and CSV files.
    Make sure to handle any errors appropriately.
    """,
    model=OpenAIChatCompletionsModel(
        model=external_provider["model"],
        openai_client=external_provider["client"],
    ),
    tools=[save_all_products]
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
        model=external_provider["model"],
        openai_client=external_provider["client"],
    ),
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[scraper_agent, json_agent, csv_agent]
)

async def main():
    # Print current working directory
    logger.info(f"\n=== Starting cigar comparison script ===")
    current_dir = os.getcwd()
    logger.info(f"Current working directory: {current_dir}")
    
    # Get the brand to search for
    brand = input("Enter the cigar brand to compare: ")
    logger.info(f"\nSearching for brand: {brand}")
    
    try:
        # Run the scraper agent
        logger.info("\n=== Running Scraper Agent ===")
        scraper_result = await Runner.run(
            scraper_agent,
            input=f"Search for and compare cigars of the brand '{brand}' between mikescigars.com and cigars.com. Make sure to return the results in the exact format specified."
        )
        logger.info("\nScraper Agent completed")
        
        # Extract the raw scraping results and comparison data
        raw_result = scraper_result.final_output
        logger.info("Debug - Raw scraper output: %s", raw_result)
        
        if isinstance(raw_result, str):
            try:
                raw_result = json.loads(raw_result)
                logger.info("Debug - Parsed JSON data: %s", json.dumps(raw_result, indent=2))
            except json.JSONDecodeError as e:
                logger.warning("Warning: Could not parse scraper result as JSON: %s", str(e))
                # Create empty structure if parsing fails
                raw_result = {
                    "mikes_products": [],
                    "cigars_products": [],
                    "matches": []
                }
        
        # Run the All Products Export Agent with the raw scraping results
        logger.info("=== Running All Products Export Agent ===")
        try:
            # Extract products from the raw result
            mikes_products = raw_result.get('mikes_products', [])
            cigars_products = raw_result.get('cigars_products', [])
            
            logger.info("Debug - Mike's products: %s", json.dumps(mikes_products, indent=2))
            logger.info("Debug - Cigars.com products: %s", json.dumps(cigars_products, indent=2))
            
            # Save all products
            all_products_result = await Runner.run(
                all_products_agent,
                input=json.dumps({
                    "brand": brand,
                    "mikes_products": mikes_products,
                    "cigars_products": cigars_products
                })
            )
            logger.info("\nAll Products Export Agent completed")
            
            # Save matches if any exist
            matches = raw_result.get('matches', [])
            if matches:
                logger.info("\n=== Saving Matches ===")
                current_date = datetime.now().strftime("%Y-%m-%d")
                matches_filename = os.path.join(current_dir, f"{brand.replace(' ', '_')}_matches_{current_date}.json")
                
                matches_data = {
                    "date": current_date,
                    "brand": brand,
                    "matches": matches
                }
                
                with open(matches_filename, 'w', encoding='utf-8') as f:
                    json.dump(matches_data, f, indent=2)
                logger.info(f"Matches saved to: {matches_filename}")
            
            logger.info("\n=== Final Results ===")
            logger.info(f"Found {len(mikes_products)} products on Mike's Cigars")
            logger.info(f"Found {len(cigars_products)} products on Cigars.com")
            logger.info(f"Found {len(matches)} matching products")
            
        except Exception as e:
            logger.error(f"Error processing results: {str(e)}")
            raise
        
    except Exception as e:
        logger.error(f"\nError during execution: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())