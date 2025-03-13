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

# Define output types for orchestrator
class OrchestratorOutput(BaseModel):
    scraper_results: Dict
    parser_results: Dict
    json_file: str
    csv_file: str

# Define the Orchestrator Agent with handoffs to specialized agents
orchestrator_agent = Agent(
    name="Cigar Comparison Orchestrator",
    instructions="""
    You are an orchestrator agent that coordinates the complete cigar comparison workflow.
    Follow these steps EXACTLY:

    1. Extract the brand name from the user's input.
       - Log: f"Processing request for brand: {brand}"

    2. Call the scraper_agent:
       - Input: f"Scrape products for brand '{brand}' from both websites"
       - Store the complete result in scraper_results
       - Log: f"Scraper found {len(scraper_results['mikes_products'])} Mike's products and {len(scraper_results['cigars_products'])} Cigars.com products"

    3. Call the html_parser_agent:
       - Input: f"Parse products for brand '{brand}' from both websites"
       - Store the complete result in parser_results
       - Log: f"Parser found {len(parser_results['mikes_products'])} Mike's products and {len(parser_results['cigars_products'])} Cigars.com products"

    4. Call the json_agent:
       - Input: {
           "brand": brand,
           "scraper_results": scraper_results,
           "parser_results": parser_results
         }
       - Store the result.json_file path
       - Log: f"Saved comparison data to {result.json_file}"

    5. Call the csv_agent:
       - Input: {"json_file": result.json_file}
       - Store the result.csv_file path
       - Log: f"Converted data to CSV: {result.csv_file}"

    6. Return the EXACT structure:
    {
        "scraper_results": scraper_results,
        "parser_results": parser_results,
        "json_file": result.json_file,
        "csv_file": result.csv_file
    }

    IMPORTANT:
    - Log EVERY step and result
    - Verify EVERY agent response
    - Include ALL product data in exports
    - Handle errors with clear messages
    - Ensure data is properly passed between agents
    - Validate file paths exist after export
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[scraper_agent, html_parser_agent, json_agent, csv_agent]
) 