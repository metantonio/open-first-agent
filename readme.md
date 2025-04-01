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

0. **Install NPM to be able to use MCP**

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
   pip install -r requirements.txt
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

**Experimental Mac UI / Debug mode:**
```bash
python experimental_ui.py
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
   - Provide the necessary data and tell to the AI to execute certain command in a EC2 instance.

3. **Development Tools**
   - IDE setup and configuration
   - Environment management
   - Jupyter notebook automation

4. **Code Conversion**
   - Conversion of SAS programming code to Python. Eg.:
  ```sh
   in the output folder I have a file named example_sas.sas I want convert it to python using and put the resulted block of code in a file named example_sas.py
  ```
   - Ask to the AI to use or not certain libraries in the result.

5. **Terminal Mode**
   - Execute a Terminal 

6. **Execute commands in the chat mode**
   - Execute commands in the chat mode using `!`. Eg: `!ls -la` 

## Notes

To let MCP to have access to folders, you must change permission of the targeted folder, Eg: `chmod 777 ./openai_mcp/sample_files`

## 📝 License

This project is licensed under a modified MIT License with non-commercial restrictions. The software is owned by Qualex Consulting Services, INC and Antonio Martínez. While you are free to use, modify, and distribute this software, you may not use it for any commercial purposes or monetary gain. See the [LICENSE](LICENSE) file for details.

**Special Provisions:**
- All contributions become the property of Qualex Consulting Services, INC and Antonio Martínez

## 🤝 Contributing

By contributing to this project, you agree to the following terms:
1. You transfer all rights of your contributed code to Qualex Consulting Services, INC and Antonio Martínez
2. Your contributions may be used, modified, or sold as part of this software by the owners
3. Your contributions will fall under the same license terms as this software

Please read our [LICENSE](LICENSE) file for complete terms before submitting pull requests.
