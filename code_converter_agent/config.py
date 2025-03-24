"""
Configuration settings for the SAS to Python code converter.
"""
import os
from dotenv import load_dotenv
from agents import AsyncOpenAI, OpenAIChatCompletionsModel

# Load environment variables
load_dotenv()

# Get provider configurations from environment variables
DEFAULT_PROVIDER = os.getenv('CODE_CONVERTER_PROVIDER', 'ollama')

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

# Mapping of SAS procedures to their Python equivalents
PROC_MAPPINGS = {
    'proc print': {
        'python_import': 'import pandas as pd',
        'template': 'print({dataset}.head({n}))'
    },
    'proc means': {
        'python_import': 'import pandas as pd',
        'template': '{dataset}.describe()'
    },
    'proc freq': {
        'python_import': 'import pandas as pd',
        'template': '{dataset}[{variables}].value_counts()'
    },
    'proc sort': {
        'python_import': 'import pandas as pd',
        'template': '{dataset}.sort_values(by={by}, ascending={ascending})'
    }
}

# SAS to Python data type mappings
DATA_TYPE_MAPPINGS = {
    'char': 'str',
    'varchar': 'str',
    'numeric': 'float64',
    'integer': 'int64',
    'date': 'datetime64[ns]',
    'datetime': 'datetime64[ns]'
}

# Default settings
DEFAULT_SETTINGS = {
    'date_format': '%Y-%m-%d',
    'datetime_format': '%Y-%m-%d %H:%M:%S',
    'missing_value': 'np.nan',
    'encoding': 'utf-8'
}

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        }
    }
} 