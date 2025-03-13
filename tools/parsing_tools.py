import requests
from bs4 import BeautifulSoup
import logging
import re
from agents import function_tool

logger = logging.getLogger(__name__)

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
        logger.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        # Look for common product containers
        product_containers = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(term in x.lower() for term in ['product', 'item', 'result']))
        
        if not product_containers:
            # Try alternative approach - look for price elements
            price_elements = soup.find_all(['span', 'div'], class_=lambda x: x and any(term in x.lower() for term in ['price', 'cost', 'amount']))
            for price_elem in price_elements:
                product = extract_product_from_price(price_elem, website_name, brand)
                if product:
                    products.append(product)
        else:
            for container in product_containers:
                product = extract_product_info(container, website_name, brand)
                if product:
                    products.append(product)
        
        logger.info(f"Found {len(products)} products using generic HTML parsing on {website_name}")
        return products
        
    except Exception as e:
        logger.error(f"Error parsing {website_name}: {str(e)}")
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
    from datetime import datetime
    import os
    import csv
    
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