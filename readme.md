# Cigar Price Comparison Agent

A Python-based intelligent agent system that compares cigar prices across different online retailers using OpenAI's GPT models and/or Open Source Models.

## Overview

This project implements a multi-agent system that scrapes, compares, and analyzes cigar prices from multiple online retailers. It uses specialized agents for different tasks, orchestrated by a main agent to provide comprehensive price comparisons and product matching.

## Features

- Multi-agent architecture for distributed tasks
- Web scraping with both selector-based and generic HTML parsing approaches
- Intelligent product matching across different websites
- Export functionality to both JSON and CSV formats
- Detailed logging and error handling
- Configurable model settings and parameters

## Project Structure

```
cigar_agents/
├── __init__.py
├── config.py
├── orchestrator_agent.py
├── scraper_agent.py
├── html_parser_agent.py
├── export_agents.py
tools/
├── __init__.py
├── scraping_tools.py
├── parsing_tools.py
└── export_tools.py
```

### Components

- **Orchestrator Agent**: Coordinates the workflow between specialized agents
- **Scraper Agent**: Handles website-specific scraping using CSS selectors
- **HTML Parser Agent**: Performs generic HTML parsing for product information
- **Export Agents**: Handle data export to JSON and CSV formats

## Installation

1. Clone the repository and create an enviroment:
```bash
git clone https://github.com/metantonio/open-first-agent
cd cigar-price-comparison
conda create -n openai-first-agent python=3.10
conda activate openai-first-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key'
```

## Usage

Run the main script:
```bash
python main.py
```

The script will:
1. Prompt for a cigar brand to search
2. Scrape product information from supported websites
3. Compare prices and find matching products
4. Export results to JSON and CSV files
5. Provide a summary of findings

## Configuration

The project uses a configuration system that allows customization of:
- Model settings (temperature, max tokens, etc.)
- Export file paths and formats
- Logging levels and output locations
- Website-specific parameters

## Development

To extend the project:
1. Add new agents in the `cigar_agents` directory
2. Implement new tools in the `tools` directory
3. Update the orchestrator agent to utilize new components
4. Maintain consistent error handling and logging

## Error Handling

The system implements comprehensive error handling:
- Graceful handling of website unavailability
- Validation of scraped data
- Logging of all operations and errors
- Fallback mechanisms for failed operations

## Logging

Logs are written to `cigar_scraper.log` and include:
- Scraping operations and results
- Product matching details
- Export operations
- Error messages and stack traces

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT