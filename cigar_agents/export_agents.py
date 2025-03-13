from typing import Dict, List
from pydantic import BaseModel
from agents import Agent, ModelSettings
from .config import get_model_config
from tools.export_tools import save_to_json, convert_json_to_csv, save_all_products

# Define output types for export agents
class JSONExportOutput(BaseModel):
    json_file: str

class CSVExportOutput(BaseModel):
    csv_file: str

class AllProductsExportOutput(BaseModel):
    json_file: str
    csv_file: str

# Define the JSON Export Agent
json_agent = Agent(
    name="JSON Export Agent",
    instructions="""
    You are a specialized agent for saving cigar comparison data to JSON format.
    
    Your task:
    1. Extract brand and product data from input
    2. Use save_to_json() to save the comparison data
    3. Return the path to the saved JSON file
    
    Expected input format:
    {
        "brand": "brand_name",
        "scraper_results": {
            "mikes_products": [...],
            "cigars_products": [...],
            "matched_products": [...]
        },
        "parser_results": {
            "mikes_products": [...],
            "cigars_products": [...],
            "matched_products": [...]
        }
    }
    
    The output must be valid JSON with:
    - All strings using double quotes
    - No additional text or formatting
    - Exact field names as specified in JSONExportOutput
    
    Handle errors gracefully and provide clear status updates.
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    tools=[save_to_json]
)

# Define the CSV Conversion Agent
csv_agent = Agent(
    name="CSV Conversion Agent",
    instructions="""
    You are a specialized agent for converting JSON comparison data to CSV format.
    
    Your task:
    1. Extract JSON file path from input
    2. Use convert_json_to_csv() to convert the data
    3. Return the path to the saved CSV file
    
    Expected input format:
    {
        "json_file": "path/to/json/file"
    }
    
    The output must be valid JSON with:
    - All strings using double quotes
    - No additional text or formatting
    - Exact field names as specified in CSVExportOutput
    
    Handle errors gracefully and provide clear status updates.
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    tools=[convert_json_to_csv]
)

# Define the All Products Export Agent
all_products_agent = Agent(
    name="All Products Export Agent",
    instructions="""
    You are a specialized agent for saving all scraped cigar products to both JSON and CSV formats.
    
    Your tasks:
    1. Extract brand and product lists from input
    2. Use save_all_products() to save both JSON and CSV files
    3. Return paths to both saved files
    
    Expected input format:
    {
        "brand": "brand_name",
        "mikes_products": [...],
        "cigars_products": [...]
    }
    
    The output must be valid JSON with:
    - All strings using double quotes
    - No additional text or formatting
    - Exact field names as specified in AllProductsExportOutput
    
    Product list requirements:
    - Handle both matched and unmatched products
    - Maintain all product details
    - Ensure consistent formatting
    
    Handle errors appropriately and provide clear status updates.
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    tools=[save_all_products]
) 