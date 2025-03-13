from typing import Dict, List
from pydantic import BaseModel
from agents import Agent, ModelSettings
import logging
from .config import get_model_config
from tools.parsing_tools import parse_mikes_cigars_html, parse_cigars_com_html, save_detailed_products_to_csv
from tools.export_tools import save_all_products

# Configure logger
logger = logging.getLogger(__name__)

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
     4. Call save_all_products
 
     Return the results in this exact format:
     {
         "mikes_detailed_products": [list of detailed products from Mike's Cigars],
         "cigars_detailed_products": [list of detailed products from Cigars.com],
         "detailed_csv_file": "path to saved CSV file"
     }
 
     Make sure to:
     - Handle any errors appropriately
     - Extract as much information as possible from the HTML content
     - Return empty lists [] if no products are found (do not return null or undefined)
     - Log clear messages about the number of products found from each source
     - Validate that product lists are always arrays before saving
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    tools=[parse_mikes_cigars_html, parse_cigars_com_html, save_detailed_products_to_csv, save_all_products]
) 