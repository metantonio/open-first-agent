import re
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from .config import get_model_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
model = get_model_config()

@function_tool
async def convert_sas_data_step(sas_code: str) -> Dict[str, Any]:
    """Convert SAS DATA step to Python pandas code.
    
    Args:
        sas_code (str): The SAS DATA step code to convert
        
    Returns:
        Dict containing success status and converted code or error
    """
    try:
        # Basic DATA step conversion logic
        python_code = []
        python_code.append("import pandas as pd")
        python_code.append("import numpy as np")
        
        # Extract dataset name and input dataset
        data_match = re.search(r'DATA\s+(\w+);', sas_code, re.IGNORECASE)
        set_match = re.search(r'SET\s+(\w+(?:\.\w+)?);', sas_code, re.IGNORECASE)
        
        if data_match and set_match:
            output_dataset = data_match.group(1)
            input_dataset = set_match.group(1)
            
            # Convert to pandas
            python_code.append(f"{output_dataset} = {input_dataset}.copy()")
            
            # Convert variable assignments
            for line in sas_code.split(';'):
                if '=' in line and 'DATA' not in line.upper() and 'SET' not in line.upper():
                    python_code.append(line.strip() + "  # Converted from SAS")
            
            return {
                'success': True,
                'code': '\n'.join(python_code)
            }
        else:
            return {
                'success': False,
                'error': 'Could not find DATA or SET statement in SAS code'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to convert DATA step: {str(e)}"
        }

@function_tool
async def convert_sas_proc(sas_code: str) -> Dict[str, Any]:
    """Convert SAS PROC step to Python pandas code.
    
    Args:
        sas_code (str): The SAS PROC code to convert
        
    Returns:
        Dict containing success status and converted code or error
    """
    try:
        # Extract PROC type and dataset
        proc_match = re.search(r'PROC\s+(\w+)\s+DATA=(\w+(?:\.\w+)?);', sas_code, re.IGNORECASE)
        
        if not proc_match:
            return {
                'success': False,
                'error': 'Could not identify PROC type and dataset'
            }
            
        proc_type = proc_match.group(1).lower()
        dataset = proc_match.group(2)
        
        # Map common PROC types to pandas operations
        proc_mappings = {
            'print': f"print({dataset}.head())",
            'means': f"{dataset}.describe()",
            'freq': f"{dataset}.value_counts()",
            'sort': f"{dataset}.sort_values(by=['$COLUMN'], ascending=True)"
        }
        
        if proc_type in proc_mappings:
            return {
                'success': True,
                'code': f"import pandas as pd\n{proc_mappings[proc_type]}"
            }
        else:
            return {
                'success': False,
                'error': f"Unsupported PROC type: {proc_type}"
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to convert PROC step: {str(e)}"
        }

@function_tool
async def convert_sas_macro(sas_code: str) -> Dict[str, Any]:
    """Convert SAS macro to Python function.
    
    Args:
        sas_code (str): The SAS macro code to convert
        
    Returns:
        Dict containing success status and converted code or error
    """
    try:
        # Extract macro name and parameters
        macro_match = re.search(r'%MACRO\s+(\w+)(?:\((.*?)\))?;', sas_code, re.IGNORECASE)
        
        if not macro_match:
            return {
                'success': False,
                'error': 'Could not identify macro definition'
            }
            
        macro_name = macro_match.group(1)
        params = macro_match.group(2) or ''
        
        # Convert parameters to Python function parameters
        python_params = ', '.join(p.strip() for p in params.split(',') if p.strip())
        
        python_code = [
            f"def {macro_name.lower()}({python_params}):",
            "    # TODO: Convert macro body",
            "    pass"
        ]
        
        return {
            'success': True,
            'code': '\n'.join(python_code)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to convert macro: {str(e)}"
        }

# Create Specialized Agents

data_step_converter = Agent(
    name="DATA Step Converter",
    instructions="""You are responsible for converting SAS DATA steps to Python pandas code.
    Your single responsibility is to:
    - Identify DATA step patterns
    - Convert dataset operations to pandas
    - Handle variable assignments
    - Maintain data integrity
    
    You MUST:
    1. Extract the DATA step code from the input
    2. Call convert_sas_data_step with the exact code
    3. Return the converted Python code or error message
    
    Example conversions:
    SAS:
    DATA mydata;
        SET sashelp.class;
        age_plus_1 = age + 1;
    RUN;
    
    Python:
    import pandas as pd
    mydata = sashelp_class.copy()
    mydata['age_plus_1'] = mydata['age'] + 1
    
    Important:
    - Preserve variable names
    - Handle missing values correctly
    - Convert SAS functions to pandas equivalents
    - Maintain data types""",
    model=model,
    tools=[convert_sas_data_step]
)

proc_converter = Agent(
    name="PROC Converter",
    instructions="""You are responsible for converting SAS PROC steps to Python pandas code.
    Your single responsibility is to:
    - Identify PROC type and parameters
    - Convert to equivalent pandas operations
    - Handle PROC-specific options
    
    You MUST:
    1. Extract the PROC step code from the input
    2. Call convert_sas_proc with the exact code
    3. Return the converted Python code or error message
    
    Example conversions:
    SAS:
    PROC MEANS DATA=sashelp.class;
    RUN;
    
    Python:
    import pandas as pd
    sashelp_class.describe()
    
    Important:
    - Map PROC types to pandas methods
    - Handle PROC options appropriately
    - Preserve statistical accuracy
    - Return equivalent Python functionality""",
    model=model,
    tools=[convert_sas_proc]
)

macro_converter = Agent(
    name="Macro Converter",
    instructions="""You are responsible for converting SAS macros to Python functions.
    Your single responsibility is to:
    - Convert macro definitions to Python functions
    - Handle macro parameters
    - Convert macro variables
    
    You MUST:
    1. Extract the macro code from the input
    2. Call convert_sas_macro with the exact code
    3. Return the converted Python code or error message
    
    Example conversions:
    SAS:
    %MACRO calculate_mean(var);
        PROC MEANS DATA=&dataset;
            VAR &var;
        RUN;
    %MEND;
    
    Python:
    def calculate_mean(var, dataset):
        return dataset[var].mean()
    
    Important:
    - Convert macro parameters to function arguments
    - Handle macro variables appropriately
    - Maintain scope and variable access
    - Preserve functionality""",
    model=model,
    tools=[convert_sas_macro]
)

# Create Main Orchestrator Agent

code_converter_orchestrator = Agent(
    name="Code Converter Orchestrator",
    instructions="""You are the main orchestrator for converting SAS code to Python code.
    Your responsibilities include:
    
    1. Code Analysis:
       - Parse SAS code to identify components (DATA, PROC, MACRO)
       - Break down complex code into convertible units
       - Maintain code sequence and dependencies
    
    2. Conversion Workflow:
       - Route code segments to appropriate specialized agents:
         * DATA steps → data_step_converter
         * PROC steps → proc_converter
         * Macros → macro_converter
       - Combine converted segments in correct order
       - Ensure all necessary imports are included
       - Verify converted code integrity
    
    3. Error Handling:
       - Catch and report conversion errors
       - Provide helpful error messages
       - Suggest alternatives for unsupported features
    
    4. Code Organization:
       - Maintain logical code structure
       - Group related conversions
       - Add appropriate comments
       - Format output code properly
    
    Example workflow:
    1. Receive SAS code
    2. Identify code components
    3. Convert each component using specialized agents
    4. Combine converted code
    5. Add necessary imports
    6. Format and return result
    
    Important:
    - Preserve code functionality
    - Maintain data integrity
    - Handle dependencies correctly
    - Provide clear error messages
    - Add helpful comments in converted code""",
    model=model,
    tools=[convert_sas_data_step, convert_sas_proc, convert_sas_macro],
    handoffs=[data_step_converter, proc_converter, macro_converter]
)

def run_workflow(sas_code: str) -> str:
    """Run the code conversion workflow with the orchestrator as the main controller."""
    logger.info("Starting code conversion workflow")
    
    try:
        # Create a new Runner instance
        response = Runner.run_sync(
            code_converter_orchestrator,
            sas_code
        )
        
        if not response:
            return "No response received from orchestrator"
        
        # Extract the Python code from the response
        output = response.final_output
        
        # If the output contains markdown code blocks, extract just the Python code
        if "```python" in output:
            code_blocks = re.findall(r'```python\n(.*?)```', output, re.DOTALL)
            if code_blocks:
                output = '\n\n'.join(code_blocks)
        
        # Ensure consistent formatting
        output = output.strip()
        if not output.startswith('import'):
            output = 'import pandas as pd\nimport numpy as np\n\n' + output
            
        return output
        
    except Exception as e:
        logger.error(f"Error in code conversion workflow: {str(e)}")
        return f"Error converting code: {str(e)}" 