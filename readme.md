# Cigar Comparison Tool using Ollama

A multi-agent system built with OpenAI Agents SDK that compares cigar products from different retailers.

## Overview

This tool scrapes two popular cigar websites (mikescigars.com and cigars.com), compares products from a specified brand, and exports the comparison data in both JSON and CSV formats. It utilizes multiple specialized AI agents to handle different aspects of the workflow.

## Features

- Web scraping from multiple cigar retailer websites
- Intelligent product matching across retailers
- Automated data export with current date
- Format conversion from JSON to CSV
- Error handling for network and parsing issues

## Prerequisites

- Python 3.10+
- Conda or another virtual environment manager
- OpenAI API key

## Installation

1. Clone this repository
```bash
git clone https://github.com/metantonio/openai-first-agent.git
cd openai-first-agent
```

2. Create and activate a conda environment
```bash
conda create -n openai-first-agent python=3.10
conda activate openai-first-agent
```

3. Install required packages
```bash
pip install openai-agents requests beautifulsoup4 pandas
```

4. Set your OpenAI API key
```bash
export OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Run the main script
```bash
python main.py
```

2. Enter the cigar brand you want to compare when prompted
```
Enter the cigar brand to compare: Davidoff
```

3. The script will output the locations of the generated JSON and CSV files with the comparison data

## How It Works

The tool uses a system of four specialized agents:

1. **Orchestrator Agent**: Coordinates the entire workflow and delegates tasks to specialized agents
2. **Scraper Agent**: Navigates websites, extracts product data, and identifies matching products
3. **JSON Export Agent**: Saves comparison data to a JSON file with the current date
4. **CSV Conversion Agent**: Converts the JSON data to a CSV table format

## Customization

- Modify the scraping selectors in the scrape functions if website layouts change
- Adjust the product matching algorithm by modifying the `similar_product_names` function
- Add additional retailers by creating new scraping functions and updating the comparison logic

## Limitations

- Web scraping is dependent on the current website structure and may break if sites change
- Product matching is based on name similarity and may miss some matches or create false positives
- Rate limiting or IP blocking may occur if too many requests are made to retailers' websites

## License

MIT

## Disclaimer

This tool is for educational purposes only. Be sure to review the terms of service for any website you scrape and ensure your usage complies with their policies.