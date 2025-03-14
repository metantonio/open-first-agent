# Multi-Agent System for Web Automation

This project implements multiple intelligent agent systems for web automation tasks, including cigar price comparison and DuckDuckGo search automation using OpenAI's GPT models and/or Open Source Models.

## Overview

The project consists of two main agent systems:
1. **Cigar Price Comparison Agent**: Scrapes, compares, and analyzes cigar prices from multiple online retailers
2. **Duck Browser Agent**: Automates DuckDuckGo searches and result processing

## Project Structure

```
.
├── cigar_agents/                 # Cigar price comparison agents
│   ├── __init__.py
│   ├── config.py                # Configuration for cigar agents
│   ├── orchestrator_agent.py    # Main orchestrator for cigar operations
│   ├── scraper_agent.py        # Website-specific scraping
│   ├── html_parser_agent.py    # Generic HTML parsing
│   └── export_agents.py        # Data export handling
├── duck_browser_agent/          # DuckDuckGo search automation
│   ├── __init__.py
│   ├── config.py               # Configuration for duck browser agent
│   └── dds_agent.py           # DuckDuckGo search agent
├── tools/                      # Shared tools and utilities
├── ui.py                       # Chainlit UI for duck browser agent
├── main.py                     # Main script for cigar agents
└── requirements.txt            # Project dependencies
```

## Agent Systems

### 1. Cigar Price Comparison Agents

A multi-agent system that works together to compare cigar prices:

- **Orchestrator Agent**: Coordinates the workflow between specialized agents
- **Scraper Agent**: Handles website-specific scraping using CSS selectors
- **HTML Parser Agent**: Performs generic HTML parsing for product information
- **Export Agents**: Handle data export to JSON and CSV formats

### 2. Duck Browser Agent

An intelligent agent that interacts with DuckDuckGo search:

- **DDS Agent**: Performs automated searches and processes results
- **Chainlit UI**: Interactive web interface for the agent

## Installation

1. Clone the repository and create an environment:
```bash
git clone https://github.com/metantonio/open-first-agent
cd open-first-agent
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

## Running the Agents

### Running the Cigar Price Comparison Agent

1. Navigate to the project directory
2. Run the main script:
```bash
python main.py
```

The script will:
- Prompt for a cigar brand to search
- Scrape product information from supported websites
- Compare prices and find matching products
- Export results to JSON and CSV files
- Provide a summary of findings

### Running the Duck Browser Agent

1. Navigate to the project directory
2. Start the Chainlit UI:
```bash
chainlit run ui.py
```

This will:
- Launch a web interface at http://localhost:8000
- Allow you to interact with the DuckDuckGo search agent
- Process and display search results through the UI

## Features

- Multi-agent architecture for distributed tasks
- Web scraping with both selector-based and generic HTML parsing approaches
- Intelligent product matching across different websites
- Export functionality to both JSON and CSV formats
- Detailed logging and error handling
- Configurable model settings and parameters

## Configuration

The project uses a configuration system for both agent types that allows customization of:
- Model settings (temperature, max tokens, etc.)
- Export file paths and formats
- Logging levels and output locations
- Website-specific parameters

### API Key Requirements

The OpenAI API key has different requirements depending on your usage:

1. **Using OpenAI Models**:
   - A valid OpenAI API key with credits is **required**
   - The key is used for both model calls and trace logging
   - Set up the key as shown in the installation steps above

2. **Using Local LLMs (e.g., Ollama)**:
   - No OpenAI credits are required for model calls
   - A valid OpenAI API key is still required for trace logging
   - You can use a free API key with no credits
   - If you don't need tracing, you can skip the API key setup

### Model Configuration

Both agent systems use `config.py` files that allow you to configure which LLM provider to use. The system supports both local and cloud-based models:

1. **Using Local Models (Default)**
```python
# External LLM provider configuration (e.g., Ollama)
external_provider = {
    "model": "qwen2.5-coder:14b",
    "client": AsyncOpenAI(base_url="http://localhost:11434/v1")
}
```

2. **Using OpenAI Models**
```python
# OpenAI provider configuration
openai_provider = {
    "model": "gpt-4",
    "client": AsyncOpenAI()
}
```

Make sure to:
1. Have the appropriate API keys set up for your chosen provider
2. Install and configure Ollama if using local models
3. Set the OPENAI_API_KEY environment variable if using OpenAI models

## Development

To extend the project:
1. Add new agents in either the `cigar_agents` or `duck_browser_agent` directories
2. Implement new tools in the `tools` directory
3. Update the respective agent configurations
4. Maintain consistent error handling and logging

## Error Handling

The system implements comprehensive error handling:
- Graceful handling of website unavailability
- Validation of scraped data
- Logging of all operations and errors
- Fallback mechanisms for failed operations

## Logging

Each agent system maintains its own logs:

### Cigar Agents
- Logs are written to `cigar_scraper.log`
- Includes scraping operations, product matching details, and export operations

### Duck Browser Agent
- Logs are displayed in the Chainlit UI
- Includes search operations and result processing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT