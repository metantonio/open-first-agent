from typing import Dict, List, Union
from pydantic import BaseModel
from agents import Agent, ModelSettings
import logging
import json
import os
from .config import get_model_config
from .scraper_agent import scraper_agent
from .html_parser_agent import html_parser_agent
from .export_agents import json_agent, csv_agent

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(ch)

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
     You are an orchestrator agent that coordinates the cigar comparison workflow.
     
     1. First, understand the user's request for which cigar brand to compare.
     2. Hand off to the Scraper Agent to scrape and compare products.
     3. Hand off to the JSON Export Agent to save the comparison data.
     4. Hand off to the CSV Conversion Agent to convert the data to CSV format.
     5. Finally, summarize the results to the user.
     
     Be helpful and informative throughout the process.
    """,
    model=get_model_config(),
    model_settings=ModelSettings(temperature=0.1),
    handoffs=[scraper_agent, json_agent, csv_agent]
) 