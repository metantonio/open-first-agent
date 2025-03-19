"""Configuration for the agents system."""
from agents import AsyncOpenAI, OpenAIChatCompletionsModel

# External LLM provider by default with ollama (if you are going to use Ollama, LLMStudio)
external_provider = {
    "model": "qwen2.5-coder:7b",
    "client": AsyncOpenAI(base_url="http://localhost:11434/v1")
}

# If you are going to use OpenAI use this provider
openai_provider = {
    "model": "gpt-4o",
    "client": AsyncOpenAI()
}

def get_model_config(provider=external_provider):
    """Get the model configuration for agents."""
    return OpenAIChatCompletionsModel(
        model=provider["model"],
        openai_client=provider["client"],
    ) 