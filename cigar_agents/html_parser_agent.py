from typing import Dict, List
from pydantic import BaseModel
from agents import Agent, ModelSettings
from .config import get_model_config
from tools.parsing_tools import parse_generic_html, extract_product_info

# Define the HTML Parser Agent that uses generic parsing
html_parser_agent = Agent(
    name="HTML Parser Agent",
    instructions="""
    You are a specialized agent for parsing HTML content from cigar websites.
    
    Your tasks:
    1. Use parse_generic_html() to get the raw HTML content from both websites
    2. Use extract_product_info() to find all product details without relying on specific selectors
    3. Compare products between sites to find matches
    4. Return all results in a structured format
    
    The output must be valid JSON with:
    - All strings using double quotes
    - No additional text or formatting
    - Exact field names as specified in HTMLParserOutput
    
    Product data requirements:
    - Each product must have name and price
    - Validate all extracted data
    - Handle missing or malformed data gracefully
    
    Handle errors appropriately and provide clear status updates.
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    tools=[parse_generic_html, extract_product_info]
) 