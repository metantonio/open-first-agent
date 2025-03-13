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
   - If you don't need tracing, you can skip the API key setup, but read OpenAI Agents SDK

To disable tracing and use local LLMs without an OpenAI API key, modify the logging configuration in your code.

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

### Model Configuration (config.py)

The `config.py` file allows you to configure which LLM provider to use for the agents. The system supports both local and cloud-based models:

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
    "model": "gpt-4o",
    "client": AsyncOpenAI()
}
```

To switch between providers, modify the `get_model_config()` call in your agent:
```python
# For local models (default)
model = get_model_config()  # Uses external_provider by default

# For OpenAI models
model = get_model_config(provider=openai_provider)
```

Make sure to:
1. Have the appropriate API keys set up for your chosen provider
2. Install and configure Ollama if using local models
3. Set the OPENAI_API_KEY environment variable if using OpenAI models

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