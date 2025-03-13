from typing import Dict, List, Union
from pydantic import BaseModel
from agents import Agent, ModelSettings
import logging
from .config import get_model_config
from .scraper_agent import scraper_agent
from .html_parser_agent import html_parser_agent
from .export_agents import json_agent, csv_agent

# Configure logger
logger = logging.getLogger(__name__)

# Define the Orchestrator Agent with handoffs to specialized agents
orchestrator_agent = Agent(
    name="Cigar Comparison Orchestrator",
    instructions="""
    You are an orchestrator agent that coordinates the complete cigar comparison workflow.
    Follow these steps EXACTLY:

    1. Extract the brand name from the user's input.
       - Log: f"Processing request for brand: {brand}"

    2. Call the scraper_agent:
       - Input: f"Compare cigars of the brand '{brand}' between websites"
       - Store the complete result
       - Log: f"Scraper found {len(result.mikes_products)} Mike's products and {len(result.cigars_products)} Cigars.com products"

    3. Call the html_parser_agent:
       - Input: f"Parse and extract products for brand '{brand}' from both websites"
       - Store the complete result
       - Log: f"Parser found {len(result.mikes_products)} Mike's products and {len(result.cigars_products)} Cigars.com products"

    4. Call the json_agent:
       - Input: Combined data from both scraper and parser
       - Store the result.json_file path
       - Log: f"Saved comparison data to {result.json_file}"

    5. Call the csv_agent:
       - Input: Path to the JSON file
       - Store the result.csv_file path
       - Log: f"Converted data to CSV: {result.csv_file}"

    6. Return the EXACT structure:
    {
        "scraper_results": {
            "mikes_products": [...],
            "cigars_products": [...],
            "matched_products": [...]
        },
        "parser_results": {
            "mikes_products": [...],
            "cigars_products": [...],
            "matched_products": [...]
        },
        "json_file": "path/to/json",
        "csv_file": "path/to/csv"
    }

    IMPORTANT:
    - Log EVERY step and result
    - Verify EVERY agent response
    - Include ALL product data in exports
    - Handle errors with clear messages
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[scraper_agent, html_parser_agent, json_agent, csv_agent]
) 