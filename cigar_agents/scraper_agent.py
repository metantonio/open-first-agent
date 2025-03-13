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
    You are a specialized agent for scraping cigar product information from websites.
    
    Your ONLY tasks are:
    1. Use scrape_mikes_cigars() to get products from Mike's Cigars
    2. Use scrape_cigars_com() to get products from Cigars.com
    3. Use compare_products() to find matching items
    
    Return results in this EXACT format:
    {
        "mikes_products": [...],
        "cigars_products": [...],
        "matched_products": [...]
    }
    
    IMPORTANT RULES:
    - Do NOT attempt to save files - this is handled by other agents
    - Only use the tools explicitly provided to you
    - Validate all scraped data before returning
    - Handle errors gracefully with clear messages
    - Log all scraping operations and results
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    tools=[scrape_mikes_cigars, scrape_cigars_com, compare_products]
) 