from typing import Dict, List, Union
from pydantic import BaseModel
from agents import Agent, ModelSettings
import logging
from .config import get_model_config
from .scraper_agent import scraper_agent
from .html_parser_agent import html_parser_agent
from .export_agents import json_agent, csv_agent
import os

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
    Follow these steps EXACTLY in order:

    1. Extract the brand name from the user's input.
       - Log: f"Processing request for brand: {brand}"

    2. Call the scraper_agent to get initial results:
       - Input MUST be: {"brand": brand}
       - Store the complete result in scraper_results
       - Log: f"Received scraper results: {scraper_results}"
       - Validate that scraper_results contains the expected keys
       - Log: f"Scraper found {len(scraper_results['mikes_products'])} Mike's products and {len(scraper_results['cigars_products'])} Cigars.com products"

    3. Call the html_parser_agent to get detailed results:
       - Input MUST be: {"brand": brand}
       - Store the complete result in parser_results
       - Log: f"Received parser results: {parser_results}"
       - Validate that parser_results contains the expected keys
       - Log: f"Parser found {len(parser_results['mikes_products'])} Mike's products and {len(parser_results['cigars_products'])} Cigars.com products"

    4. Call the json_agent to save the combined results:
       - First log: "Preparing to save JSON data"
       - Input MUST be EXACTLY:
         {
           "brand": brand,
           "comparison_data": {
               "scraper_results": scraper_results,
               "parser_results": parser_results
           }
         }
       - Log the input data: f"Sending data to JSON agent: {input_data}"
       - The response will be a dictionary with "json_file" key
       - Store the result.json_file path
       - Verify the file exists: os.path.exists(result.json_file)
       - Log: f"JSON file created at: {result.json_file}"

    5. Call the csv_agent to convert the JSON:
       - First log: "Preparing to convert to CSV"
       - Input MUST be EXACTLY: {"json_file": result.json_file}
       - Log: f"Sending JSON file path to CSV agent: {result.json_file}"
       - The response will be a dictionary with "csv_file" key
       - Store the result.csv_file path
       - Verify the file exists: os.path.exists(result.csv_file)
       - Log: f"CSV file created at: {result.csv_file}"

    6. Return the EXACT structure:
    {
        "scraper_results": scraper_results,
        "parser_results": parser_results,
        "json_file": result.json_file,
        "csv_file": result.csv_file
    }

    IMPORTANT RULES:
    - Each agent must ONLY use its own designated tools
    - The scraper_agent and html_parser_agent MUST NOT try to save files directly
    - ALL file saving operations MUST go through json_agent or csv_agent
    - Handle errors with clear messages
    - Log EVERY step with detailed information
    - Validate all data before passing between agents
    - VERIFY that files exist after export operations
    - If any step fails:
      1. Log the error details
      2. Try to continue with remaining steps
      3. Include error information in the final response
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[scraper_agent, html_parser_agent, json_agent, csv_agent]
) 