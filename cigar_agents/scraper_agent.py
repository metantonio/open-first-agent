from typing import Dict, List
from pydantic import BaseModel
from agents import Agent, ModelSettings
import logging
from .config import get_model_config
from tools.scraping_tools import scrape_mikes_cigars, scrape_cigars_com, compare_products

# Configure logger
logger = logging.getLogger(__name__)

# Define the Scraper Agent that uses specific CSS selectors
scraper_agent = Agent(
    name="Cigar Website Scraper",
    instructions="""
    You are a specialized agent for scraping cigar product data from specific websites.
    
    Your tasks:
    1. Use the scrape_mikes_cigars() function to get products from Mike's Cigars
    2. Use the scrape_cigars_com() function to get products from Cigars.com
    3. Use the compare_products() function to find matching items
    4. Return all results in a structured format
    
    The output must be valid JSON with:
    - All strings using double quotes
    - No additional text or formatting
    - Exact field names as specified in ScraperOutput
    
    IMPORTANT:
    - You MUST log the results after each step using the logger
    - You MUST verify that the product lists are not empty before comparison
    - You MUST include ALL found products in the output
    - You MUST return the COMPLETE lists in the output, not just matches
    
    Example of expected output structure:
    {
        "mikes_products": [{"name": "...", "price": "...", "url": "..."}],
        "cigars_products": [{"name": "...", "price": "...", "url": "..."}],
        "matched_products": [{"mikes": {...}, "cigars": {...}}]
    }
    
    Handle errors gracefully and provide clear status updates.
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    tools=[scrape_mikes_cigars, scrape_cigars_com, compare_products]
) 