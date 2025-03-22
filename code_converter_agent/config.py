"""
Configuration settings for the SAS to Python code converter.
"""
from agents import AsyncOpenAI, OpenAIChatCompletionsModel

# External LLM provider by default with ollama
external_provider = {
    "model": "qwen2.5-coder:14b",
    "client": AsyncOpenAI(base_url="http://localhost:11434/v1")
}

# OpenAI provider configuration
openai_provider = {
    "model": "gpt-4",
    "client": AsyncOpenAI()
}

def get_model_config(provider=external_provider):
    """Get the model configuration for agents."""
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