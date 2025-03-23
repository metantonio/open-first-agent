"""Configuration for the Ochestrator agent system."""
from agents import AsyncOpenAI, OpenAIChatCompletionsModel

# External LLM provider by default with ollama
external_provider = {
    "model": "qwen2.5-coder:14b",
    "client": AsyncOpenAI(base_url="http://localhost:11434/v1")
}

# OpenAI provider configuration
openai_provider = {
    "model": "gpt-4o",
    "client": AsyncOpenAI()
}

TEMPERATURE = 0.1

def get_model_config(provider=external_provider):
    """Get the model configuration for agents."""
    return OpenAIChatCompletionsModel(
        model=provider["model"],
        openai_client=provider["client"],
    ) 