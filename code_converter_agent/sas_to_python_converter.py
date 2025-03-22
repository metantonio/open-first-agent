import re
from typing import Dict, List, Optional, Tuple, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SasToPythonConverter:
    """
    A class to convert SAS code to Python code.
    Handles various SAS procedures and data steps conversion to equivalent Python code.
    """
    
    def __init__(self):
        self.python_imports = set([
            "import pandas as pd",
            "import numpy as np",
            "from pathlib import Path"
        ])
        self.sas_data_sets = {}  # Store SAS dataset references
        
    def convert(self, sas_code: str) -> str:
        """
        Convert SAS code to Python code.
        
        Args:
            sas_code (str): The SAS code to convert
            
        Returns:
            str: The converted Python code
        """
        try:
            # Clean and normalize the input SAS code
            cleaned_code = self._clean_sas_code(sas_code)
            
            # Split code into individual statements
            statements = self._split_into_statements(cleaned_code)
            
            # Convert each statement
            python_code = []
            for stmt in statements:
                converted = self._convert_statement(stmt)
                if converted:
                    python_code.append(converted)
            
            # Add required imports
            imports = sorted(list(self.python_imports))
            
            return "\n".join(imports + [""] + python_code)
            
        except Exception as e:
            logger.error(f"Error converting SAS code: {str(e)}")
            raise
    
    def _clean_sas_code(self, code: str) -> str:
        """Clean and normalize SAS code for processing."""
        # Remove comments
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)  # Remove block comments
        code = re.sub(r'\*[^\n]*;', '', code)  # Remove line comments
        
        # Normalize whitespace
        code = re.sub(r'\s+', ' ', code)
        return code.strip()
    
    def _split_into_statements(self, code: str) -> List[str]:
        """Split SAS code into individual statements."""
        # Basic splitting by semicolon, but preserve semicolons in quoted strings
        statements = []
        current = []
        in_quotes = False
        quote_char = None
        
        for char in code:
            if char in ["'", '"'] and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
            
            current.append(char)
            
            if char == ';' and not in_quotes:
                statements.append(''.join(current).strip())
                current = []
        
        if current:  # Add any remaining code
            statements.append(''.join(current).strip())
            
        return [s for s in statements if s]
    
    def _convert_statement(self, statement: str) -> Optional[str]:
        """Convert a single SAS statement to Python code."""
        statement = statement.strip().lower()
        
        if statement.startswith('data '):
            return self._convert_data_step(statement)
        elif statement.startswith('proc '):
            return self._convert_proc_step(statement)
        elif statement.startswith('libname '):
            return self._convert_libname(statement)
        else:
            return f"# Unconverted SAS statement: {statement}"
    
    def _convert_data_step(self, statement: str) -> str:
        """Convert SAS DATA step to Python code."""
        # Basic DATA step conversion - to be expanded
        self.python_imports.add("import pandas as pd")
        return "# TODO: Implement DATA step conversion"
    
    def _convert_proc_step(self, statement: str) -> str:
        """Convert SAS PROC step to Python code."""
        # Basic PROC step conversion - to be expanded
        return "# TODO: Implement PROC step conversion"
    
    def _convert_libname(self, statement: str) -> str:
        """Convert SAS LIBNAME statement to Python code."""
        # Basic LIBNAME conversion - to be expanded
        return "# TODO: Implement LIBNAME conversion" 