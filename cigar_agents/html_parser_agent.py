from typing import Dict, List
from pydantic import BaseModel
from agents import Agent, ModelSettings
import logging
from .config import get_model_config
from tools.parsing_tools import parse_mikes_cigars_html, parse_cigars_com_html, save_detailed_products_to_csv

# Configure logger
logger = logging.getLogger(__name__)

# Define the HTML Parser Agent
html_parser_agent = Agent(
    name="HTML Parser Agent",
    instructions="""
    You are a specialized agent for parsing HTML content from cigar websites.
    
    Your tasks:
    1. Use parse_mikes_cigars_html() to get Mike's Cigars products
    2. Use parse_cigars_com_html() to get Cigars.com products
    3. Find matching products between the two sites
    
    Expected input format:
    {
        "brand": "brand_name"
    }
    
    You MUST return results in this EXACT format:
    {
        "mikes_products": [...],
        "cigars_products": [...],
        "matched_products": [...]
    }
    
    IMPORTANT RULES:
    - Only use the tools explicitly provided to you
    - Do NOT attempt to save files - this is handled by other agents
    - Validate all parsed data before returning
    - Handle errors gracefully with clear messages
    - Log all parsing operations and results
    
    For matching products:
    - Compare product names ignoring case and spacing
    - Consider products matching if they have similar names and same size/type
    - Include complete product details in matched_products
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    tools=[parse_mikes_cigars_html, parse_cigars_com_html, save_detailed_products_to_csv]
) 