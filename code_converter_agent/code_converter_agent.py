import re
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from .config import get_model_config, TEMPERATURE
import asyncio
from logger import logger

# Configure logging
""" logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) """
model = get_model_config()

def read_sas_file(file_path: str) -> str:
    """
    Read SAS code from a file, handling both absolute and relative paths.
    
    Args:
        file_path (str): Path to the SAS file (absolute or relative)
        
    Returns:
        str: Content of the SAS file
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If there's an error reading the file
    """
    try:
        # Convert to Path object to handle both Windows and Unix paths
        file_path = file_path.strip().strip("'").strip('"')
        logger.debug(f"initial path: {file_path}")
        path = Path(file_path)
        
        # If path is relative and doesn't exist, try looking in the output directory
        if not path.is_absolute() and not path.exists():
            output_path = Path('output') / path.name
            if output_path.exists():
                path = output_path
        logger.info(f"Resolved SAS file path: {path}")
        # Verify file exists and has .sas extension
        if not path.exists():
            raise FileNotFoundError(f"SAS file not found: {file_path}")
        if path.suffix.lower() != '.sas':
            raise ValueError(f"File must have .sas extension: {file_path}")
            
        # Read the file content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        logger.info(f"Successfully read SAS file: {path}")
        return content
        
    except Exception as e:
        logger.error(f"Error reading SAS file {file_path}: {str(e)}")
        raise

@function_tool
async def convert_sas_data_step(sas_code: str) -> Dict[str, Any]:
    """Convert SAS DATA step to Python pandas code."""
    try:
        # Ensure sas_code is a string
        if not isinstance(sas_code, str):
            sas_code = '\n'.join(sas_code) if isinstance(sas_code, list) else str(sas_code)
            
        # Extract dataset name and input dataset, handling case where SET is in a string
        code_lines = [line.strip() for line in sas_code.split('\n') if line.strip()]
        
        # Find DATA and SET statements while ignoring them in quoted strings
        data_line = ''
        set_line = ''
        for line in code_lines:
            # Skip lines that are entirely within quotes
            if (line.count('"') % 2 == 0) and (line.count("'") % 2 == 0):
                if 'DATA' in line.upper() and not data_line:
                    data_line = line
                elif 'SET' in line.upper() and not set_line:
                    set_line = line
        
        data_match = re.search(r'DATA\s+(\w+);', data_line, re.IGNORECASE)
        set_match = re.search(r'SET\s+(\w+(?:\.\w+)?);', set_line, re.IGNORECASE)
        
        if not (data_match and set_match):
            return {
                'success': False,
                'error': 'Could not find DATA or SET statement in SAS code'
            }
            
        output_dataset = data_match.group(1)
        input_dataset = set_match.group(1)
        
        # Build Python code
        python_code = []
        python_code.append("import pandas as pd")
        python_code.append("import numpy as np")
        python_code.append("")
        python_code.append(f"# Create a copy of the input dataset")
        python_code.append(f"{output_dataset} = {input_dataset}.copy()")
        
        # Convert variable assignments
        for line in code_lines:
            line = line.strip()
            if '=' in line and 'DATA' not in line.upper() and 'SET' not in line.upper():
                # Handle quoted strings by preserving the entire line
                if '"' in line or "'" in line:
                    # Remove trailing semicolon and add to DataFrame
                    var_name = line.split('=')[0].strip()
                    expression = line.split('=', 1)[1].strip()
                    # Remove trailing semicolon but preserve semicolons in quotes
                    if expression.endswith(';'):
                        expression = expression[:-1]
                    python_code.append(f"{output_dataset}['{var_name}'] = {expression}")
                else:
                    # Add DataFrame reference for variable assignments
                    var_name = line.split('=')[0].strip()
                    expression = line.split('=')[1].strip().rstrip(';')
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
        dataset = proc_match.group(2)  # Keep dataset name exactly as is
        
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
    2. Call convert_sas_data_step with the ENTIRE code block as a single string
    3. When you get a response, extract ONLY the 'code' field if success=true
    4. Return the extracted code WITHOUT any markdown or JSON formatting
    5. If there's an error, return the error message prefixed with "Error: "
    
    Example input:
    DATA mydata;
        SET sashelp.class;
        age_plus_1 = age + 1;
        string_var = "Hello; World";
    RUN;
    
    Example output:
    import pandas as pd
    import numpy as np

    mydata = sashelp.class.copy()
    mydata['age_plus_1'] = mydata['age'] + 1
    mydata['string_var'] = "Hello; World"
    
    Important:
    - NEVER wrap output in markdown code blocks or JSON
    - Return ONLY the Python code or error message as plain text
    - Preserve variable names and string contents exactly""",
    model=model,
    tools=[convert_sas_data_step],
    model_settings=ModelSettings(temperature=TEMPERATURE)
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
    3. When you get a response, extract ONLY the 'code' field if success=true
    4. Return the extracted code WITHOUT any markdown or JSON formatting
    5. If there's an error, return the error message prefixed with "Error: "
    
    Example input:
    PROC MEANS DATA=sashelp.class;
    RUN;
    
    Example output:
    import pandas as pd
    import numpy as np

    sashelp.class.describe()
    
    Important:
    - NEVER wrap output in markdown code blocks or JSON
    - Return ONLY the Python code or error message as plain text
    - Preserve dataset names exactly""",
    model=model,
    tools=[convert_sas_proc],
    model_settings=ModelSettings(temperature=TEMPERATURE)
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
    3. When you get a response, extract ONLY the 'code' field if success=true
    4. Return the extracted code WITHOUT any markdown or JSON formatting
    5. If there's an error, return the error message prefixed with "Error: "
    
    Example input:
    %MACRO calculate_mean(var);
        PROC MEANS DATA=&dataset;
            VAR &var;
        RUN;
    %MEND;
    
    Example output:
    import pandas as pd
    import numpy as np

    def calculate_mean(var, dataset):
        return dataset[var].mean()
    
    Important:
    - NEVER wrap output in markdown code blocks or JSON
    - Return ONLY the Python code or error message as plain text
    - Convert macro parameters exactly""",
    model=model,
    tools=[convert_sas_macro],
    model_settings=ModelSettings(temperature=TEMPERATURE)
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
       For each code segment:
       
       a) If it's a MACRO (starts with %MACRO):
          - Use convert_sas_macro
          - Extract the 'code' field from response
          - Include the function definition
       
       b) If it's a DATA step (starts with DATA):
          - Use convert_sas_data_step
          - Extract the 'code' field from response
          - Include the dataset operations
       
       c) If it's a PROC step (starts with PROC):
          - Use convert_sas_proc
          - Extract the 'code' field from response
          - Include the pandas operations
    
    3. Error Handling:
       - Handle each component separately
       - If one component fails, continue with others
       - Return error messages exactly as received
       - Prefix any new error messages with "Error: "
    
    4. Code Organization:
       - Keep imports at the top (only include once)
       - Group related conversions
       - Maintain proper indentation
       - Preserve comments
    
    You MUST:
    1. Use the exact tool functions provided
    2. Extract ONLY the 'code' field from tool responses
    3. Combine multiple code segments with proper spacing
    4. Return the final code WITHOUT any markdown or JSON formatting
    5. Preserve dataset names exactly as in SAS
    6. Handle quoted strings carefully
    
    Example macro conversion:
    Input:
    %MACRO calculate_mean(var);
        PROC MEANS DATA=&dataset;
            VAR &var;
        RUN;
    %MEND;
    
    Output:
    import pandas as pd
    import numpy as np

    def calculate_mean(var, dataset):
        return dataset[var].mean()
    
    Example complex conversion:
    Input:
    %MACRO process_data;
        DATA mydata;
            SET sashelp.class;
            age_plus_1 = age + 1;
        RUN;
        
        PROC MEANS DATA=mydata;
        RUN;
    %MEND;
    
    Output:
    import pandas as pd
    import numpy as np

    def process_data():
        mydata = sashelp.class.copy()
        mydata['age_plus_1'] = mydata['age'] + 1
        return mydata.describe()""",
    model=model,
    tools=[convert_sas_data_step, convert_sas_proc, convert_sas_macro],
    model_settings=ModelSettings(temperature=TEMPERATURE)
)

async def run_workflow(sas_input: str) -> str:
    """Run the code conversion workflow with the orchestrator as the main controller."""
    logger.info("Starting code conversion workflow")
    
    try:
        # If input is a file path, read the file

        if isinstance(sas_input, str) and (
            (sas_input.lower().endswith('.sas') or '/' in sas_input or '\\' in sas_input) 
            and '/*' not in sas_input 
            and not any(kw in sas_input.lower() for kw in ['data ', 'proc ', '%macro'])
        ):
            try:
                sas_input = sas_input.strip().strip("'").strip('"')
                logger.info(f"sas_input should be a file path: {sas_input}")
                sas_code = read_sas_file(sas_input)
            except Exception as e:
                logger.error(f"Failed to read SAS file: {str(e)}")
                return f"Error: Failed to read SAS file - {str(e)}"
        else:
            # Input is the actual SAS code
            sas_code = sas_input
            
        # Log received content
        logger.info("Code Converter Agent: Received SAS code for conversion")
        logger.info(f"Code Converter Agent: Input content length: {len(str(sas_code))} characters")
        logger.info("Code Converter Agent: First 100 characters of input: " + str(sas_code)[:100] + "...")
        
        # Ensure we're passing a string to the Runner
        if not isinstance(sas_code, str):
            sas_code = str(sas_code)
        
        # Create a new Runner instance
        response = await Runner.run(
            code_converter_orchestrator,
            sas_code
        )
        
        # Rest of the function remains the same...
        if not response or not response.final_output:
            logger.error("Code Converter Agent: No response received from orchestrator")
            return "Error: No response received from orchestrator"
        
        output = response.final_output.strip()
        
        if output.lower().startswith('error:'):
            logger.error(f"Code Converter Agent: Conversion error - {output}")
            return output
            
        if not output:
            logger.error("Code Converter Agent: Empty response from orchestrator")
            return "Error: Empty response from orchestrator"
            
        if isinstance(output, str):
            if "```" in output:
                code_blocks = re.findall(r'```(?:python)?\n?(.*?)\n?```', output, re.DOTALL)
                if code_blocks:
                    output = '\n\n'.join(block.strip() for block in code_blocks)
            
            if '"code":' in output:
                code_blocks = re.findall(r'"code":\s*"(.*?)"', output)
                if code_blocks:
                    output = '\n\n'.join(block.replace('\\n', '\n').strip() for block in code_blocks)
            elif '"error":' in output:
                error_blocks = re.findall(r'"error":\s*"(.*?)"', output)
                if error_blocks:
                    logger.error(f"Code Converter Agent: Conversion error in response - {error_blocks[0]}")
                    return f"Error: {error_blocks[0]}"
            
            output = output.strip()
            
            if output and not output.startswith('import'):
                output = 'import pandas as pd\nimport numpy as np\n\n' + output
            
            logger.info("Code Converter Agent: Successfully converted SAS code to Python")
            logger.info(f"Code Converter Agent: Output content length: {len(output)} characters")
            logger.info("Code Converter Agent: First 100 characters of output: " + output[:100] + "...")
            
            return output
        else:
            logger.error("Code Converter Agent: Invalid response format from orchestrator")
            return "Error: Invalid response format from orchestrator"
        
    except Exception as e:
        logger.error(f"Code Converter Agent: Error in code conversion workflow - {str(e)}")
        return f"Error: {str(e)}"

def run_workflow_sync(request: str) -> str:
    """Synchronous wrapper for the async workflow."""
    try:
        return asyncio.get_event_loop().run_until_complete(run_workflow(request))
    except RuntimeError as e:
        if "no running event loop" in str(e):
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(run_workflow(request))
            finally:
                loop.close()
        raise