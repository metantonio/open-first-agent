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
import ast
import re

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
    "model":"qwen2.5-coder:14b",
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
    
    # Filter out error entries and ensure we have lists
    if not isinstance(mikes_products, list):
        mikes_products = []
    if not isinstance(cigars_products, list):
        cigars_products = []
    
    mikes_products = [p for p in mikes_products if isinstance(p, dict) and "error" not in p]
    cigars_products = [p for p in cigars_products if isinstance(p, dict) and "error" not in p]
    
    all_products_data = {
        "date": current_date,
        "brand": brand,
        "mikes_cigars_products": mikes_products,
        "cigars_com_products": cigars_products
    }
    
    # Save to JSON
    json_filename = os.path.join(current_dir, f"{brand.replace(' ', '_')}_all_products_{current_date}.json")
    try:
        with open(json_filename, 'w+', encoding='utf-8') as f:
            json.dump(all_products_data, f, indent=2)
        logger.info(f"All products JSON file created successfully at: {json_filename}")
    except Exception as e:
        logger.error(f"Error creating all products JSON file: {str(e)}")
        return {"error": str(e)}
    
    # Save to CSV
    csv_filename = json_filename.replace('.json', '.csv')
    try:
        with open(csv_filename, 'w+', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Date', 'Brand', 'Website', 'Product Name', 'Price', 'URL'])
            
            # Write Mike's Cigars products
            for product in mikes_products:
                if isinstance(product, dict):
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
                if isinstance(product, dict):
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
        return {"error": str(e)}
    
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
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        # Common product container patterns
        product_patterns = [
            {'class_': lambda x: x and any(pattern in str(x).lower() for pattern in ['product', 'item', 'card', 'listing'])},
            {'itemtype': 'http://schema.org/Product'},
            {'data-product-id': True},
            {'class_': lambda x: x and 'product' in str(x).lower()}
        ]
        
        # Try each pattern to find product containers
        for pattern in product_patterns:
            containers = soup.find_all(**pattern)
            if containers:
                logger.info(f"Found {len(containers)} potential products using pattern: {pattern}")
                for container in containers:
                    try:
                        # Extract product information
                        product = extract_product_info(container, website_name, brand)
                        if product:
                            products.append(product)
                    except Exception as e:
                        logger.error(f"Error extracting product info: {str(e)}")
                        continue
        
        # If no products found, try alternative search methods
        if not products:
            logger.info("No products found with standard patterns, trying alternative methods")
            # Look for price patterns
            price_elements = soup.find_all(text=re.compile(r'\$\d+\.?\d*'))
            for price_elem in price_elements:
                try:
                    product = extract_product_from_price(price_elem, website_name, brand)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.error(f"Error extracting product from price: {str(e)}")
                    continue
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_products = []
        for product in products:
            if product['url'] not in seen_urls:
                seen_urls.add(product['url'])
                unique_products.append(product)
        
        logger.info(f"Successfully parsed {len(unique_products)} unique products from {website_name}")
        return unique_products
        
    except requests.RequestException as e:
        logger.error(f"Error fetching {website_name}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error parsing {website_name} HTML: {str(e)}")
        return []

def extract_product_info(container, website_name: str, brand: str) -> dict:
    """Helper function to extract product information from a container."""
    # Find product name
    name_candidates = [
        container.find('h1'),
        container.find('h2'),
        container.find('h3'),
        container.find(class_=lambda x: x and 'name' in str(x).lower()),
        container.find(class_=lambda x: x and 'title' in str(x).lower())
    ]
    name = None
    for candidate in name_candidates:
        if candidate and candidate.text.strip():
            name = candidate.text.strip()
            break
    
    if not name:
        return None
    
    # Find price
    price_pattern = re.compile(r'\$\d+\.?\d*')
    price_text = container.find(text=price_pattern)
    if price_text:
        price = price_pattern.search(price_text).group()
    else:
        return None
    
    # Find URL
    url = None
    link = container.find('a')
    if link and link.get('href'):
        url = link['href']
        if not url.startswith('http'):
            url = f"https://{website_name}" + ('' if url.startswith('/') else '/') + url
    else:
        return None
    
    # Only return if product matches brand and has all required fields
    if brand.lower() in name.lower():
        return {
            "website": website_name,
            "name": name,
            "price": price,
            "url": url,
            "description": get_description(container),
            "stock_status": get_stock_status(container)
        }
    return None

def extract_product_from_price(price_elem, website_name: str, brand: str) -> dict:
    """Helper function to extract product information starting from a price element."""
    container = price_elem.parent
    for _ in range(3):  # Look up to 3 levels up
        if container.name == 'body': break
        name_elem = container.find(text=re.compile(brand, re.IGNORECASE))
        if name_elem:
            name = name_elem.strip()
            url = None
            link = container.find('a')
            if link and link.get('href'):
                url = link['href']
                if not url.startswith('http'):
                    url = f"https://{website_name}" + ('' if url.startswith('/') else '/') + url
                return {
                    "website": website_name,
                    "name": name,
                    "price": price_elem.strip(),
                    "url": url,
                    "description": get_description(container),
                    "stock_status": get_stock_status(container)
                }
        container = container.parent
    return None

def get_description(container) -> str:
    """Helper function to extract product description."""
    desc_candidates = [
        container.find(class_=lambda x: x and 'description' in str(x).lower()),
        container.find(class_=lambda x: x and 'details' in str(x).lower()),
        container.find('p')
    ]
    for candidate in desc_candidates:
        if candidate and candidate.text.strip():
            return candidate.text.strip()
    return "N/A"

def get_stock_status(container) -> str:
    """Helper function to extract stock status."""
    stock_patterns = ['in stock', 'out of stock', 'available', 'unavailable']
    for pattern in stock_patterns:
        status = container.find(text=re.compile(pattern, re.IGNORECASE))
        if status:
            return status.strip()
    return "N/A"

@function_tool
def parse_mikes_cigars_html(brand: str) -> list:
    """
    Parse Mike's Cigars HTML using the generic parser.
    
    Args:
        brand: The cigar brand to search for
    
    Returns:
        List of products with detailed information
    """
    logger.info("parse mikes cigars html function")
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
    logger.info("parse cigars html function")
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
    1. First, call scrape_mikes_cigars(brand) and store the COMPLETE result
    2. Then, call scrape_cigars_com(brand) and store the COMPLETE result
    3. Finally, call compare_products with the EXACT lists from steps 1 and 2

    CRITICAL: You must ONLY return this exact JSON structure:
    {
        "mikes_products": <result from step 1>,
        "cigars_products": <result from step 2>,
        "matches": <result from step 3>
    }

    JSON Requirements:
    - Use DOUBLE QUOTES for ALL strings (both keys and values)
    - No single quotes allowed
    - No line breaks within arrays or objects
    - No additional text before or after the JSON
    - No markdown formatting
    - No comments or explanations

    EXAMPLE CORRECT OUTPUT:
    {"mikes_products":[{"website":"mikescigars.com","name":"Example","price":"$25.00"}],"cigars_products":[],"matches":[]}

    If any function call fails:
    - Return empty arrays for the products
    - Still maintain the exact JSON structure with double quotes
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
    Your task is to save ALL products from both websites to JSON and CSV files.
    
    Follow these steps:
    1. Take the complete lists of products from both websites
    2. Call save_all_products with the EXACT lists and brand name
    3. Return the EXACT result from save_all_products
    
    Important:
    - Do not modify or filter the product lists
    - Pass the exact lists to save_all_products
    - Return the exact result from save_all_products
    - Do not add any text or formatting to the response
    - Handle any errors by returning the error object from save_all_products
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
    Your task is to extract detailed product information from both websites.

    Follow these steps exactly:
    1. Call parse_mikes_cigars_html(brand) and store its result
       - Ensure you properly handle the response and validate it contains products
       - If no products are found, log a warning but continue
    
    2. Call parse_cigars_com_html(brand) and store its result
       - Ensure you properly handle the response and validate it contains products
       - If no products are found, log a warning but continue
    
    3. Only if either website returned products:
       Call save_detailed_products_to_csv with both lists and brand
    
    4. Return ONLY this exact JSON structure:
    {
        "mikes_detailed_products": <result from step 1>,
        "cigars_detailed_products": <result from step 2>,
        "detailed_csv_file": <result from step 3 or null if no products>
    }

    IMPORTANT PARSING REQUIREMENTS:
    - For each product found, ensure it has at minimum: name, price, and URL
    - Clean up product names by removing excess whitespace
    - Validate prices are in proper format (e.g. "$XX.XX")
    - Ensure URLs are complete (add domain if needed)
    - Filter out any products that don't match the requested brand
    
    ERROR HANDLING:
    - If a parsing function fails, return an empty list for that website
    - If both websites fail, return empty lists and null for the CSV file
    - Log any parsing errors or warnings
    
    DO NOT:
    - Include any text before or after the JSON
    - Include any code or code examples
    - Add any explanations or comments
    - Use markdown formatting
    - Add line breaks within the JSON
    - Add any additional fields
    - Modify the function results structure
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
    
    # Initialize variables with proper structure
    mikes_products = []
    cigars_products = []
    matches = []
    parser_output = {
        "mikes_detailed_products": [],
        "cigars_detailed_products": [],
        "detailed_csv_file": None
    }
    
    try:
        # Get the brand to search for
        brand = input("Enter the cigar brand to compare: ").strip()
        if not brand:
            logger.error("Brand name cannot be empty")
            return
        logger.info(f"\nSearching for brand: {brand}")
        
        # Run the scraper agent
        logger.info("\n=== Running Scraper Agent ===")
        try:
            scraper_result = await Runner.run(
                scraper_agent,
                input=f"Search for cigars of the brand '{brand}'. Execute the scraping functions in order and return a properly formatted JSON object with the results."
            )
            logger.info("\nScraper Agent completed")
            
            # Process scraper results with improved error handling
            raw_result = scraper_result.final_output
            if isinstance(raw_result, str):
                # Clean up the raw output
                raw_result = raw_result.replace('```json\n', '').replace('```\n', '').replace('```', '')
                raw_result = raw_result.strip()
                
                # Find the JSON object in the string
                json_start = raw_result.find('{')
                json_end = raw_result.rfind('}')
                if json_start >= 0 and json_end > json_start:
                    raw_result = raw_result[json_start:json_end + 1]
                
                try:
                    raw_result = json.loads(raw_result)
                except json.JSONDecodeError:
                    try:
                        raw_result = ast.literal_eval(raw_result)
                    except (SyntaxError, ValueError) as e:
                        logger.error(f"Failed to parse scraper output: {str(e)}")
                        raw_result = {"mikes_products": [], "cigars_products": [], "matches": []}
            
            # Extract and validate data
            if isinstance(raw_result, dict):
                mikes_products = raw_result.get('mikes_products', [])
                cigars_products = raw_result.get('cigars_products', [])
                matches = raw_result.get('matches', [])
                
                # Validate data types
                if not all(isinstance(x, list) for x in [mikes_products, cigars_products, matches]):
                    logger.error("Invalid data types in scraper results")
                    mikes_products, cigars_products, matches = [], [], []
                
                # Filter out invalid entries
                mikes_products = [p for p in mikes_products if isinstance(p, dict) and all(k in p for k in ['name', 'price', 'url'])]
                cigars_products = [p for p in cigars_products if isinstance(p, dict) and all(k in p for k in ['name', 'price', 'url'])]
                matches = [m for m in matches if isinstance(m, dict)]
                
                logger.info("\nValidated scraper results:")
                logger.info(f"- Found {len(mikes_products)} Mike's Cigars products")
                logger.info(f"- Found {len(cigars_products)} Cigars.com products")
                logger.info(f"- Found {len(matches)} matching products")
            else:
                logger.error(f"Unexpected scraper result type: {type(raw_result)}")
        except Exception as e:
            logger.error(f"Error in Scraper Agent execution: {str(e)}")
        
        # Run the HTML Parser Agent with improved error handling
        logger.info("\n=== Running HTML Parser Agent ===")
        try:
            parser_result = await Runner.run(
                html_parser_agent,
                input=f"Parse HTML and extract detailed product information for the brand '{brand}'. Execute the parsing functions in order and return a properly formatted JSON object with the results."
            )
            logger.info("\nHTML Parser Agent completed")
            
            # Process HTML Parser results with improved validation
            raw_parser_output = parser_result.final_output
            if isinstance(raw_parser_output, str):
                raw_parser_output = raw_parser_output.replace('```json\n', '').replace('```\n', '').replace('```', '')
                raw_parser_output = raw_parser_output.strip()
                
                json_start = raw_parser_output.find('{')
                json_end = raw_parser_output.rfind('}')
                if json_start >= 0 and json_end > json_start:
                    raw_parser_output = raw_parser_output[json_start:json_end + 1]
                
                try:
                    parser_output = json.loads(raw_parser_output)
                except json.JSONDecodeError:
                    try:
                        parser_output = ast.literal_eval(raw_parser_output)
                    except (SyntaxError, ValueError) as e:
                        logger.error(f"Failed to parse HTML parser output: {str(e)}")
                        parser_output = {
                            "mikes_detailed_products": [],
                            "cigars_detailed_products": [],
                            "detailed_csv_file": None
                        }
            
            # Validate parser output
            if isinstance(parser_output, dict):
                mikes_detailed = parser_output.get('mikes_detailed_products', [])
                cigars_detailed = parser_output.get('cigars_detailed_products', [])
                csv_file = parser_output.get('detailed_csv_file')
                
                # Validate data types and required fields
                if not isinstance(mikes_detailed, list) or not isinstance(cigars_detailed, list):
                    logger.error("Invalid data types in parser results")
                    mikes_detailed, cigars_detailed = [], []
                
                # Filter out invalid entries
                mikes_detailed = [p for p in mikes_detailed if isinstance(p, dict) and all(k in p for k in ['name', 'price', 'url'])]
                cigars_detailed = [p for p in cigars_detailed if isinstance(p, dict) and all(k in p for k in ['name', 'price', 'url'])]
                
                parser_output = {
                    "mikes_detailed_products": mikes_detailed,
                    "cigars_detailed_products": cigars_detailed,
                    "detailed_csv_file": csv_file if isinstance(csv_file, str) else None
                }
                
                logger.info("\nHTML Parser found:")
                logger.info(f"- {len(mikes_detailed)} detailed products from Mike's Cigars")
                logger.info(f"- {len(cigars_detailed)} detailed products from Cigars.com")
                if csv_file:
                    logger.info(f"- Saved detailed products to: {csv_file}")
            else:
                logger.error(f"Unexpected parser result type: {type(parser_output)}")
        except Exception as e:
            logger.error(f"Error in HTML Parser execution: {str(e)}")
        
        # Run the All Products Export Agent
        if mikes_products or cigars_products:
            logger.info("\n=== Running All Products Export Agent ===")
            try:
                all_products_result = await Runner.run(
                    all_products_agent,
                    input=json.dumps({
                        "brand": brand,
                        "mikes_products": mikes_products,
                        "cigars_products": cigars_products
                    })
                )
                logger.info("\nAll Products Export Agent completed")
            except Exception as e:
                logger.error(f"Error in All Products Export Agent execution: {str(e)}")
        
        # Save matches if any exist
        if matches:
            try:
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
            except Exception as e:
                logger.error(f"Error saving matches: {str(e)}")
        
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
        logger.error(f"\nUnexpected error during execution: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        logger.info("\n=== Script completed ===")

if __name__ == "__main__":
    asyncio.run(main())