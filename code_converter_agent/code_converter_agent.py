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
    """Convert SAS DATA step to Python pandas code."""
    try:
        # Extract dataset name and input dataset
        data_match = re.search(r'DATA\s+(\w+);', sas_code, re.IGNORECASE)
        set_match = re.search(r'SET\s+(\w+(?:\.\w+)?);', sas_code, re.IGNORECASE)
        
        if not (data_match and set_match):
            return {
                'success': False,
                'error': 'Could not find DATA or SET statement in SAS code'
            }
            
        output_dataset = data_match.group(1)
        input_dataset = set_match.group(1).replace('.', '_')
        
        # Build Python code
        python_code = []
        python_code.append("import pandas as pd")
        python_code.append("import numpy as np")
        python_code.append("")
        python_code.append(f"# Create a copy of the input dataset")
        python_code.append(f"{output_dataset} = {input_dataset}.copy()")
        
        # Convert variable assignments
        for line in sas_code.split(';'):
            line = line.strip()
            if '=' in line and 'DATA' not in line.upper() and 'SET' not in line.upper():
                # Handle quoted strings carefully
                if '"' in line or "'" in line:
                    python_code.append(line)
                else:
                    # Add DataFrame reference for variable assignments
                    var_name = line.split('=')[0].strip()
                    expression = line.split('=')[1].strip()
                    python_code.append(f"{output_dataset}['{var_name}'] = {output_dataset}[{expression}]")
        
        return {
            'success': True,
            'code': '\n'.join(python_code)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Error converting DATA step: {str(e)}"
        }

@function_tool
async def convert_sas_proc(sas_code: str) -> Dict[str, Any]:
    """Convert SAS PROC step to Python pandas code."""
    try:
        # Extract PROC type and dataset
        proc_match = re.search(r'PROC\s+(\w+)\s+DATA=(\w+(?:\.\w+)?);', sas_code, re.IGNORECASE)
        
        if not proc_match:
            return {
                'success': False,
                'error': 'Could not identify PROC type and dataset'
            }
            
        proc_type = proc_match.group(1).lower()
        dataset = proc_match.group(2).replace('.', '_')
        
        # Map common PROC types to pandas operations
        proc_mappings = {
            'print': f"print({dataset}.head())",
            'means': f"{dataset}.describe()",
            'freq': f"{dataset}.value_counts()",
            'sort': f"{dataset}.sort_values(by=['$COLUMN'], ascending=True)"
        }
        
        if proc_type in proc_mappings:
            python_code = [
                "import pandas as pd",
                "import numpy as np",
                "",
                f"# Equivalent to PROC {proc_type.upper()}",
                proc_mappings[proc_type]
            ]
            return {
                'success': True,
                'code': '\n'.join(python_code)
            }
        else:
            return {
                'success': False,
                'error': f"Unsupported PROC type: {proc_type}"
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Error converting PROC step: {str(e)}"
        }

@function_tool
async def convert_sas_macro(sas_code: str) -> Dict[str, Any]:
    """Convert SAS macro to Python function."""
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
        
        # Extract macro body
        body_match = re.search(r'%MACRO.*?;(.*?)%MEND', sas_code, re.IGNORECASE | re.DOTALL)
        body = body_match.group(1) if body_match else ''
        
        python_code = [
            "import pandas as pd",
            "import numpy as np",
            "",
            f"def {macro_name.lower()}({python_params}):",
            "    # Converted from SAS macro"
        ]
        
        # Convert macro body if present
        if body.strip():
            # Add basic implementation
            python_code.extend([
                "    # TODO: Implement full macro body conversion",
                "    # Original SAS code:",
                *[f"    # {line.strip()}" for line in body.split('\n') if line.strip()],
                "    pass"
            ])
        else:
            python_code.append("    pass")
        
        return {
            'success': True,
            'code': '\n'.join(python_code)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Error converting macro: {str(e)}"
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
    3. Return ONLY the converted Python code from the response, no additional text
    4. If there's an error, return the error message prefixed with "Error: "
    
    Example conversions:
    SAS:
    DATA mydata;
        SET sashelp.class;
        age_plus_1 = age + 1;
    RUN;
    
    Python:
    import pandas as pd
    import numpy as np

    mydata = sashelp_class.copy()
    mydata['age_plus_1'] = mydata['age'] + 1
    
    Important:
    - Do not add any explanatory text or markdown formatting
    - Return only the Python code or error message
    - Preserve variable names exactly as they appear
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
    3. Return ONLY the converted Python code from the response, no additional text
    4. If there's an error, return the error message prefixed with "Error: "
    
    Example conversions:
    SAS:
    PROC MEANS DATA=sashelp.class;
    RUN;
    
    Python:
    import pandas as pd
    import numpy as np

    sashelp_class.describe()
    
    Important:
    - Do not add any explanatory text or markdown formatting
    - Return only the Python code or error message
    - Map PROC types to pandas methods exactly
    - Handle PROC options appropriately
    - Preserve statistical accuracy""",
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
    3. Return ONLY the converted Python code from the response, no additional text
    4. If there's an error, return the error message prefixed with "Error: "
    
    Example conversions:
    SAS:
    %MACRO calculate_mean(var);
        PROC MEANS DATA=&dataset;
            VAR &var;
        RUN;
    %MEND;
    
    Python:
    import pandas as pd
    import numpy as np

    def calculate_mean(var, dataset):
        return dataset[var].mean()
    
    Important:
    - Do not add any explanatory text or markdown formatting
    - Return only the Python code or error message
    - Convert macro parameters to function arguments exactly
    - Handle macro variables appropriately
    - Maintain scope and variable access""",
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
       - Return ONLY the final converted Python code
    
    3. Error Handling:
       - If any component fails to convert, return the error message
       - Prefix all error messages with "Error: "
    
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
    5. Return only the final Python code
    
    Important:
    - Do not include any explanatory text or markdown formatting
    - Return only the Python code or error message
    - Preserve code functionality exactly
    - Maintain data integrity
    - Handle dependencies correctly""",
    model=model,
    tools=[convert_sas_data_step, convert_sas_proc, convert_sas_macro]
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
            return "Error: No response received from orchestrator"
        
        # Extract the Python code from the response
        output = response.final_output
        
        # If the output contains markdown code blocks, extract just the Python code
        if "```python" in output:
            code_blocks = re.findall(r'```python\n(.*?)```', output, re.DOTALL)
            if code_blocks:
                output = '\n\n'.join(code_blocks)
        
        # If the output contains tool call JSON, extract just the code
        if '"function":' in output:
            # Extract code from successful tool responses
            code_blocks = []
            for tool_response in re.findall(r'"code":\s*"([^"]*)"', output):
                code_blocks.append(tool_response.replace('\\n', '\n'))
            if code_blocks:
                output = '\n\n'.join(code_blocks)
        
        # Clean up the output
        output = output.strip()
        
        # Handle error messages
        if 'error:' in output.lower():
            return output if output.lower().startswith('error:') else f"Error: {output}"
        
        # Ensure consistent formatting
        if output and not output.startswith('import'):
            output = 'import pandas as pd\nimport numpy as np\n\n' + output
            
        return output
        
    except Exception as e:
        logger.error(f"Error in code conversion workflow: {str(e)}")
        return f"Error: {str(e)}" 