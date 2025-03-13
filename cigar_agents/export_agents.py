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
    1. Log: "Starting JSON export"
    2. STRICTLY validate input has required fields:
       - Must have "brand" (string)
       - Must have "comparison_data" (dict) containing:
         - "scraper_results" (dict) with: mikes_products, cigars_products, matched_products
         - "parser_results" (dict) with: mikes_products, cigars_products, matched_products
       - Log any missing fields as errors
    3. Call save_to_json() with EXACTLY:
       save_to_json(
           comparison_data=input["comparison_data"],
           brand=input["brand"]
       )
    4. The result MUST be a file path string
    5. Return EXACTLY: {"json_file": result}
    
    Example valid input:
    {
        "brand": "Davidoff",
        "comparison_data": {
            "scraper_results": {
                "mikes_products": [{"name": "...", "price": "...", "url": "..."}],
                "cigars_products": [{"name": "...", "price": "...", "url": "..."}],
                "matched_products": []
            },
            "parser_results": {
                "mikes_products": [{"name": "...", "price": "...", "url": "..."}],
                "cigars_products": [{"name": "...", "price": "...", "url": "..."}],
                "matched_products": []
            }
        }
    }
    
    IMPORTANT:
    - Log EVERY step with detailed information
    - Validate ALL input data before processing
    - Return ONLY a dictionary with "json_file" key
    - If any error occurs:
      1. Log the full error details
      2. Include error information in the response
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
    1. Log: "Starting CSV conversion"
    2. STRICTLY validate input:
       - Must have "json_file" (string) pointing to an existing JSON file
       - The JSON file must contain the expected data structure
       - Log any validation errors
    3. Call convert_json_to_csv() with EXACTLY:
       convert_json_to_csv(json_file=input["json_file"])
    4. The result MUST be a file path string
    5. Return EXACTLY: {"csv_file": result}
    
    Example valid input:
    {
        "json_file": "/absolute/path/to/comparison_data.json"
    }
    
    IMPORTANT:
    - Log EVERY step with detailed information
    - Verify the JSON file exists before attempting conversion
    - Return ONLY a dictionary with "csv_file" key
    - If any error occurs:
      1. Log the full error details
      2. Include error information in the response
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