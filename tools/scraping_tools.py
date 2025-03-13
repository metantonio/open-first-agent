import requests
from bs4 import BeautifulSoup
import logging
from agents import function_tool

logger = logging.getLogger(__name__)

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