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
        product_items = soup.select('.main-brand')
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

@function_tool
def parse_generic_html(url: str, website_name: str, brand: str) -> list:
    """
    Generic HTML parser that analyzes the body content to find product information
    without relying on specific CSS selectors.
    
    Args:
        url: The URL to scrape
        website_name: Name of the website being scraped
        brand: The brand being searched
    
    Returns:
        List of products with detailed information
    """
    logger.info(f"Starting generic HTML parsing for {website_name}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        body = soup.find('body')
        products = []
        
        # Find all potential product containers
        # Look for common patterns in product listings
        potential_containers = []
        
        # 1. Find elements that contain both price patterns and product names
        price_patterns = ['$', 'USD', 'Price:', 'price', '.00']
        for pattern in price_patterns:
            elements = body.find_all(text=lambda text: text and pattern in text)
            for element in elements:
                container = element.parent
                # Go up the tree to find a reasonable container
                for _ in range(3):  # Check up to 3 levels up
                    if container.find_all(text=True, recursive=False):
                        potential_containers.append(container)
                    container = container.parent
        
        # 2. Find elements that look like product cards/items
        common_product_classes = ['product', 'item', 'card', 'listing', 'brand']
        for class_pattern in common_product_classes:
            elements = body.find_all(class_=lambda x: x and class_pattern.lower() in x.lower())
            potential_containers.extend(elements)
        
        # Remove duplicates while preserving order
        seen = set()
        potential_containers = [x for x in potential_containers if not (x in seen or seen.add(x))]
        
        logger.info(f"Found {len(potential_containers)} potential product containers")
        
        for container in potential_containers:
            try:
                # Extract all text nodes and links from the container
                texts = [text.strip() for text in container.stripped_strings]
                links = container.find_all('a')
                
                if not texts:
                    continue
                
                # Find product name (usually the longest text that's not a description)
                name = max((t for t in texts if len(t) < 200), key=len, default="N/A")
                
                # Find price (text containing price patterns)
                price = "N/A"
                for text in texts:
                    if any(pattern in text for pattern in price_patterns):
                        price = text.strip()
                        break
                
                # Find URL (first link in container)
                url = next((link.get('href', '') for link in links), '')
                if url and not url.startswith('http'):
                    url = f"https://{website_name}" + url
                
                # Find description (longest text)
                description = max(texts, key=len, default="N/A")
                if description == name:
                    description = "N/A"
                
                # Find stock status (look for common patterns)
                stock_patterns = ['in stock', 'out of stock', 'available', 'unavailable']
                stock_status = next(
                    (text for text in texts if any(pattern in text.lower() for pattern in stock_patterns)),
                    "N/A"
                )
                
                # Additional attributes (look for patterns like SKU, ratings, etc.)
                additional_info = {}
                sku_patterns = ['sku', 'item #', 'product code']
                rating_patterns = ['rating', 'stars', '/5']
                
                for text in texts:
                    text_lower = text.lower()
                    if any(pattern in text_lower for pattern in sku_patterns):
                        additional_info['sku'] = text
                    elif any(pattern in text_lower for pattern in rating_patterns):
                        additional_info['rating'] = text
                
                # Only create product if we found at least a name and price
                if name != "N/A" and price != "N/A":
                    product = {
                        "website": website_name,
                        "name": name,
                        "price": price,
                        "url": url,
                        "description": description,
                        "stock_status": stock_status,
                        "brand": brand,
                        **additional_info
                    }
                    
                    # Verify this looks like a valid product
                    if brand.lower() in name.lower() or brand.lower() in description.lower():
                        products.append(product)
                        logger.info(f"Found product: {name}")
                
            except Exception as e:
                logger.error(f"Error parsing container: {str(e)}")
                continue
        
        logger.info(f"Successfully parsed {len(products)} products from {website_name}")
        return products
        
    except Exception as e:
        logger.error(f"Error parsing {website_name} HTML: {str(e)}")
        return []

@function_tool
def parse_mikes_cigars_html(brand: str) -> list:
    """
    Parse Mike's Cigars HTML using the generic parser.
    
    Args:
        brand: The cigar brand to search for
    
    Returns:
        List of products with detailed information
    """
    url = f"https://mikescigars.com/catalogsearch/result/?q={brand.replace(' ', '+')}"
    return parse_generic_html(url, "mikescigars.com", brand)

@function_tool
def parse_cigars_com_html(brand: str) -> list:
    """
    Parse Cigars.com HTML using the generic parser.
    
    Args:
        brand: The cigar brand to search for
    
    Returns:
        List of products with detailed information
    """
    url = f"https://www.cigars.com/search?lang=en_US&jrSubmitButton=&q={brand.replace(' ', '+')}"
    return parse_generic_html(url, "cigars.com", brand)

@function_tool
def save_detailed_products_to_csv(mikes_products: list, cigars_products: list, brand: str) -> str:
    """
    Save detailed product information to a CSV file.
    
    Args:
        mikes_products: List of detailed products from Mike's Cigars
        cigars_products: List of detailed products from Cigars.com
        brand: The brand being searched
    
    Returns:
        Path to the created CSV file
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_dir = os.getcwd()
    csv_filename = os.path.join(current_dir, f"{brand.replace(' ', '_')}_detailed_products_{current_date}.csv")
    
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header with all possible fields
            writer.writerow([
                'Date', 'Brand', 'Website', 'Product Name', 'Price', 'URL',
                'Description', 'SKU/Rating', 'Stock Status'
            ])
            
            # Write Mike's Cigars products
            for product in mikes_products:
                writer.writerow([
                    current_date,
                    product.get('brand', 'N/A'),
                    product.get('website', 'N/A'),
                    product.get('name', 'N/A'),
                    product.get('price', 'N/A'),
                    product.get('url', 'N/A'),
                    product.get('description', 'N/A'),
                    product.get('sku', 'N/A'),
                    product.get('stock_status', 'N/A')
                ])
            
            # Write Cigars.com products
            for product in cigars_products:
                writer.writerow([
                    current_date,
                    product.get('brand', 'N/A'),
                    product.get('website', 'N/A'),
                    product.get('name', 'N/A'),
                    product.get('price', 'N/A'),
                    product.get('url', 'N/A'),
                    product.get('description', 'N/A'),
                    product.get('rating', 'N/A'),
                    product.get('stock_status', 'N/A')
                ])
        
        logger.info(f"Detailed products CSV file created successfully at: {csv_filename}")
        return csv_filename
    except Exception as e:
        logger.error(f"Error creating detailed products CSV file: {str(e)}")
        raise

# Define the Scraper Agent
scraper_agent = Agent(
    name="Cigar Scraper Agent",
    instructions="""
    You are a specialized agent for scraping cigar websites. 
    Your task is to search for a specific cigar brand on Mike's Cigars and Cigars.com,
    and collect all product information.

    Follow these steps exactly:
    1. First, call scrape_mikes_cigars(brand) to get products from Mike's Cigars
    2. Then, call scrape_cigars_com(brand) to get products from Cigars.com
    3. Finally, call compare_products(mikes_products, cigars_products) with the results from steps 1 and 2

    You MUST execute these function calls in order and use their actual return values.
    DO NOT try to construct the parameters as strings or template literals.

    After executing all functions, return a JSON object in this exact format:
    {
        "mikes_products": [list of products from Mike's Cigars],
        "cigars_products": [list of products from Cigars.com],
        "matches": [list of matching products]
    }

    Make sure to:
    - Pass the brand parameter correctly to the scraping functions
    - Use the actual return values from the scraping functions in the compare_products call
    - Return a valid JSON object with the exact structure specified above
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

# Define the HTML Parser Agent
html_parser_agent = Agent(
    name="HTML Parser Agent",
    instructions="""
    You are a specialized agent for parsing HTML content from cigar websites.
    Your task is to extract detailed product information from the HTML body of both
    Mike's Cigars and Cigars.com websites.

    Follow these steps exactly:
    1. Call parse_mikes_cigars_html with the provided brand name to get detailed Mike's Cigars products
    2. Call parse_cigars_com_html with the provided brand name to get detailed Cigars.com products
    3. Call save_detailed_products_to_csv with both product lists and the brand name

    Return the results in this exact format:
    {
        "mikes_detailed_products": [list of detailed products from Mike's Cigars],
        "cigars_detailed_products": [list of detailed products from Cigars.com],
        "detailed_csv_file": "path to saved CSV file"
    }

    Make sure to handle any errors appropriately and extract as much information as possible
    from the HTML content.
    """,
    model=OpenAIChatCompletionsModel(
        model=external_provider["model"],
        openai_client=external_provider["client"],
    ),
    tools=[parse_mikes_cigars_html, parse_cigars_com_html, save_detailed_products_to_csv]
)

# Define the Orchestrator Agent with handoffs to specialized agents
orchestrator_agent = Agent(
    name="Cigar Comparison Orchestrator",
    instructions="""
    You are an orchestrator agent that coordinates the complete cigar comparison and data collection workflow.
    
    Your tasks in order:
    1. First, understand the user's request for which cigar brand to compare.
    
    2. Hand off to the Scraper Agent to:
       - Scrape and compare products using specific selectors
       - Get initial product listings and matches
    
    3. Hand off to the HTML Parser Agent to:
       - Parse the raw HTML of both websites
       - Extract detailed product information
       - Save comprehensive product details to CSV
    
    4. Hand off to the JSON Export Agent to:
       - Save the comparison data from the Scraper Agent
    
    5. Hand off to the CSV Conversion Agent to:
       - Convert the comparison data to CSV format
    
    6. Summarize all results to the user, including:
       - Number of products found by each method
       - Number of matches found
       - Locations of all saved files
    
    Make sure to track and report any differences between the products found by the
    Scraper Agent versus the HTML Parser Agent, as they might find different items
    due to their different approaches.
    
    Be helpful and informative throughout the process.
    """,
    model=OpenAIChatCompletionsModel(
        model=external_provider["model"],
        openai_client=external_provider["client"],
    ),
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[scraper_agent, html_parser_agent, json_agent, csv_agent]
)

async def main():
    # Print current working directory
    logger.info(f"\n=== Starting cigar comparison script ===")
    current_dir = os.getcwd()
    logger.info(f"Current working directory: {current_dir}")
    
    # Initialize variables
    mikes_products = []
    cigars_products = []
    matches = []
    parser_output = {
        "mikes_detailed_products": [],
        "cigars_detailed_products": [],
        "detailed_csv_file": None
    }
    
    # Get the brand to search for
    brand = input("Enter the cigar brand to compare: ")
    logger.info(f"\nSearching for brand: {brand}")
    
    try:
        # Run the scraper agent
        logger.info("\n=== Running Scraper Agent ===")
        scraper_result = await Runner.run(
            scraper_agent,
            input=f"Search for cigars of the brand '{brand}'. Execute the scraping functions in order and return a properly formatted JSON object with the results."
        )
        logger.info("\nScraper Agent completed")
        
        # Process scraper results
        raw_result = scraper_result.final_output
        logger.info("Debug - Raw scraper output: %s", raw_result)
        
        try:
            # Clean up the raw output if it contains markdown
            if isinstance(raw_result, str):
                # Remove markdown code blocks if present
                raw_result = raw_result.replace('```json\n', '').replace('```\n', '').replace('```', '')
                raw_result = raw_result.strip()
                # Remove any "Here is..." prefix text
                if raw_result.startswith('Here is'):
                    raw_result = raw_result[raw_result.find('{'):]
                raw_result = json.loads(raw_result)
            
            # Ensure we have a dictionary
            if isinstance(raw_result, dict):
                # Ensure the dictionary has all required keys
                required_keys = ['mikes_products', 'cigars_products', 'matches']
                if not all(key in raw_result for key in required_keys):
                    raise ValueError(f"Missing required keys in scraper result. Required: {required_keys}")
                
                # Update our variables
                mikes_products = raw_result['mikes_products']
                cigars_products = raw_result['cigars_products']
                matches = raw_result['matches']
                
                if not isinstance(mikes_products, list) or not isinstance(cigars_products, list):
                    raise ValueError("Products must be lists")
                
                logger.info("Validated scraper results:")
                logger.info(f"- Found {len(mikes_products)} Mike's Cigars products")
                logger.info(f"- Found {len(cigars_products)} Cigars.com products")
                logger.info(f"- Found {len(matches)} matching products")
            else:
                raise ValueError(f"Unexpected scraper result type: {type(raw_result)}")
            
        except Exception as e:
            logger.error(f"Error processing scraper results: {str(e)}")
            # Keep the initialized empty lists
        
        # Run the HTML Parser Agent
        logger.info("\n=== Running HTML Parser Agent ===")
        parser_result = await Runner.run(
            html_parser_agent,
            input=f"Parse HTML and extract detailed product information for the brand '{brand}'. Execute the parsing functions in order and return a properly formatted JSON object with the results."
        )
        logger.info("\nHTML Parser Agent completed")
        
        # Process HTML Parser results
        try:
            parser_output = parser_result.final_output
            if isinstance(parser_output, str):
                # Clean up the raw output if it contains markdown
                parser_output = parser_output.replace('```json\n', '').replace('```\n', '').replace('```', '')
                parser_output = parser_output.strip()
                # Remove any "Here is..." prefix text
                if parser_output.startswith('Here is'):
                    parser_output = parser_output[parser_output.find('{'):]
                parser_output = json.loads(parser_output)
            
            if isinstance(parser_output, dict):
                required_keys = ['mikes_detailed_products', 'cigars_detailed_products', 'detailed_csv_file']
                if not all(key in parser_output for key in required_keys):
                    raise ValueError(f"Missing required keys in parser result. Required: {required_keys}")
                
                logger.info("HTML Parser found:")
                logger.info(f"- {len(parser_output['mikes_detailed_products'])} detailed products from Mike's Cigars")
                logger.info(f"- {len(parser_output['cigars_detailed_products'])} detailed products from Cigars.com")
                logger.info(f"- Saved detailed products to: {parser_output['detailed_csv_file']}")
            else:
                raise ValueError(f"Unexpected parser result type: {type(parser_output)}")
            
        except Exception as e:
            logger.error(f"Error processing HTML Parser results: {str(e)}")
            # Keep the initialized empty dictionary
        
        # Run the All Products Export Agent
        logger.info("\n=== Running All Products Export Agent ===")
        try:
            # Use validated products from scraper
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
            
            # Print final summary
            logger.info("\n=== Final Results ===")
            logger.info(f"Basic Scraper found:")
            logger.info(f"- {len(mikes_products)} products on Mike's Cigars")
            logger.info(f"- {len(cigars_products)} products on Cigars.com")
            logger.info(f"- {len(matches)} matching products")
            
            logger.info(f"\nDetailed HTML Parser found:")
            logger.info(f"- {len(parser_output['mikes_detailed_products'])} detailed products from Mike's Cigars")
            logger.info(f"- {len(parser_output['cigars_detailed_products'])} detailed products from Cigars.com")
            if parser_output['detailed_csv_file']:
                logger.info(f"- Detailed products saved to: {parser_output['detailed_csv_file']}")
            
        except Exception as e:
            logger.error(f"Error in final processing: {str(e)}")
            raise
        
    except Exception as e:
        logger.error(f"\nError during execution: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())