# Multi-Agent System for Web Automation and Development

A powerful multi-agent system that combines various specialized AI agents to automate web tasks, manage infrastructure, and streamline development workflows using OpenAI's GPT models and/or Open Source Models.

## 🚀 Features

- **Web Automation**: Automated web scraping and search operations
- **Infrastructure Management**: Terraform configuration and AWS CLI automation
- **Development Tools**: Automated setup of development environments
- **Interactive UI**: Web-based interface for easy interaction with agents

## 📁 Project Structure

```
.
├── aws_cli_agent/           # AWS CLI automation
├── cigar_agents/           # Web scraping and price comparison
├── code_converter_agent/   # Code conversion utilities
├── dev_env_agent/         # Development environment setup
├── duck_browser_agent/    # DuckDuckGo search automation
├── explanation_agent/     # Documentation generation
├── file_system_agent/    # File system operations
├── terminal_agent/       # Terminal command automation
├── terraform_agent/      # Infrastructure as Code management using Terraform
├── tools/               # Shared utilities
├── ui.py               # Chainlit UI implementation
├── universal_orchestrator.py  # Main agent coordinator
└── various config files (.env, requirements.txt, etc.)
```

## 🛠 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/metantonio/open-first-agent
   cd open-first-agent
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   
   **Or use Conda:**

  ```bash
   conda create -n openai-first-agent python=3.10
   conda activate openai-first-agent
  ```
   

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configurations
   ```


### Running the UI Agents

1. Navigate to the project directory
2. Start the Chainlit UI:
```bash
chainlit run ui.py
```

## 🔑 Environment Variables

Required environment variables in your `.env` file:

- `OPENAI_API_KEY`: Your OpenAI API key
- `ANTHROPIC_API_KEY`: Your Anthropic API key (if using Claude)
- Additional keys based on enabled agents (AWS, etc.)

## 🚦 Getting Started`

1. **Access the web interface**
   - Open your browser to `http://localhost:8000`
   - Select the agent system you want to use
   - Follow the interactive prompts

## 📚 Available Agent Systems

1. **Web Automation**
   - Cigar price comparison
   - DuckDuckGo search automation

2. **Infrastructure Management**
   - Terraform configuration management
   - AWS CLI automation

3. **Development Tools**
   - IDE setup and configuration
   - Environment management
   - Jupyter notebook automation

4. **Code Conversion**
   - Conversion of SAS programming code to Python

## 📝 License

MIT

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.