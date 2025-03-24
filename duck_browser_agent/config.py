"""Configuration for the agents system."""
import os
from dotenv import load_dotenv
from agents import AsyncOpenAI, OpenAIChatCompletionsModel

# Load environment variables
load_dotenv()

# Get provider configurations from environment variables
DEFAULT_PROVIDER = os.getenv('DUCK_BROWSER_PROVIDER', 'ollama')

# Ollama provider configuration
ollama_provider = {
    "model": os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:14b'),
    "client": AsyncOpenAI(base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434/v1'))
}

# OpenAI provider configuration
openai_provider = {
    "model": os.getenv('OPENAI_MODEL', 'gpt-4o'),
    "client": AsyncOpenAI()
}

# Temperature setting
TEMPERATURE = 0.1

def get_provider_config(agent_name=None):
    """Get the provider configuration based on environment variables."""
    if agent_name:
        provider_name = os.getenv(f'{agent_name.upper()}_PROVIDER', DEFAULT_PROVIDER)
    else:
        provider_name = DEFAULT_PROVIDER
    
    return ollama_provider if provider_name.lower() == 'ollama' else openai_provider

def get_model_config(agent_name=None):
    """Get the model configuration for agents."""
    provider = get_provider_config(agent_name)
    return OpenAIChatCompletionsModel(
        model=provider["model"],
        openai_client=provider["client"],
    ) 