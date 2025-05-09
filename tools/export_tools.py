import json
import csv
from datetime import datetime
import os
import logging
from agents import function_tool

logger = logging.getLogger(__name__)

@function_tool
def save_to_json(comparison_data: dict, brand: str) -> str:
    """
    Save comparison data to a JSON file with current date.
    
    Args:
        comparison_data: Dictionary containing scraper and parser results
        brand: The brand being compared
    
    Returns:
        Path to the saved JSON file
    """
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get absolute path to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logger.info(f"Project root directory: {project_root}")
        
        # Create output directory if it doesn't exist
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")
        
        # Log the data structure we're about to save
        logger.info(f"Comparison data structure: {comparison_data.keys()}")
        logger.info(f"Scraper results keys: {comparison_data.get('scraper_results', {}).keys()}")
        logger.info(f"Parser results keys: {comparison_data.get('parser_results', {}).keys()}")
        
        # Prepare filename
        filename = os.path.join(output_dir, f"{brand.replace(' ', '_')}_comparison_{current_date}.json")
        logger.info(f"Will save to file: {filename}")
        
        # Ensure the data structure is correct
        output_data = {
            "date": current_date,
            "brand": brand,
            "scraper_results": comparison_data.get("scraper_results", {}),
            "parser_results": comparison_data.get("parser_results", {})
        }
        
        # Write the file with proper encoding
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
            logger.info("JSON data written to file")
        
        # Verify file was created and has content
        if not os.path.exists(filename):
            raise Exception(f"File was not created at {filename}")
        
        file_size = os.path.getsize(filename)
        if file_size == 0:
            raise Exception(f"File was created but is empty: {filename}")
        logger.info(f"JSON file created successfully, size: {file_size} bytes")
            
        return filename
        
    except Exception as e:
        logger.error(f"Error in save_to_json: {str(e)}")
        logger.error(f"Current working directory: {os.getcwd()}")
        raise

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
        logger.info(f"Starting CSV conversion from: {json_file}")
        
        # Verify input file exists
        if not os.path.exists(json_file):
            raise FileNotFoundError(f"JSON file not found at: {json_file}")
        
        # Get the file size
        json_size = os.path.getsize(json_file)
        logger.info(f"Input JSON file size: {json_size} bytes")
        
        # Read the JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"JSON data loaded, keys: {data.keys()}")
        
        # Create CSV filename
        csv_filename = json_file.replace('.json', '.csv')
        logger.info(f"Will create CSV at: {csv_filename}")
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Date', 'Brand', 'Source', 'Product Name', 'Price', 'URL', 'Description', 'Stock Status', 'Matched'])
            
            # Helper function to write products
            def write_products(products, source, results_type):
                logger.info(f"Writing {len(products)} products from {source}")
                for product in products:
                    matched = 'Yes' if any(
                        m.get('url') == product.get('url')
                        for m in data[results_type].get('matched_products', [])
                    ) else 'No'
                    
                    writer.writerow([
                        data['date'],
                        data['brand'],
                        source,
                        product.get('name', 'N/A'),
                        product.get('price', 'N/A'),
                        product.get('url', 'N/A'),
                        product.get('description', 'N/A'),
                        product.get('stock_status', 'N/A'),
                        matched
                    ])
            
            # Write scraper results
            scraper_results = data.get('scraper_results', {})
            write_products(scraper_results.get('mikes_products', []), "Mike's Cigars (Scraper)", 'scraper_results')
            write_products(scraper_results.get('cigars_products', []), "Cigars.com (Scraper)", 'scraper_results')
            
            # Write parser results
            parser_results = data.get('parser_results', {})
            write_products(parser_results.get('mikes_products', []), "Mike's Cigars (Parser)", 'parser_results')
            write_products(parser_results.get('cigars_products', []), "Cigars.com (Parser)", 'parser_results')
        
        # Verify CSV file was created
        if not os.path.exists(csv_filename):
            raise Exception(f"CSV file was not created at {csv_filename}")
        
        csv_size = os.path.getsize(csv_filename)
        if csv_size == 0:
            raise Exception(f"CSV file was created but is empty: {csv_filename}")
        logger.info(f"CSV file created successfully, size: {csv_size} bytes")
        
        return csv_filename
        
    except Exception as e:
        logger.error(f"Error in convert_json_to_csv: {str(e)}")
        logger.error(f"Current working directory: {os.getcwd()}")
        raise

@function_tool
def save_all_products(mikes_products: list, cigars_products: list, brand: str) -> dict:
    """
    Save all scraped products from both websites to JSON and CSV.
    
    Args:
        mikes_products: List of products from Mike's Cigars
        cigars_products: List of products from Cigars.com
        brand: The brand being searched
    
    Returns:
        Dictionary with paths to saved files
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)
    
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
    json_filename = os.path.join(output_dir, f"{brand.replace(' ', '_')}_all_products_{current_date}.json")
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
                    product.get('name', 'N/A'),
                    product.get('price', 'N/A'),
                    product.get('url', 'N/A')
                ])
            
            # Write Cigars.com products
            for product in cigars_products:
                writer.writerow([
                    current_date,
                    brand,
                    'cigars.com',
                    product.get('name', 'N/A'),
                    product.get('price', 'N/A'),
                    product.get('url', 'N/A')
                ])
        
        # Verify files were created
        if not os.path.exists(json_filename) or not os.path.exists(csv_filename):
            raise Exception("One or more files were not created successfully")
            
        logger.info(f"All products CSV file created successfully at: {csv_filename}")
    except Exception as e:
        logger.error(f"Error creating all products CSV file: {str(e)}")
        raise
    
    return {
        "json_file": json_filename,
        "csv_file": csv_filename
    }

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