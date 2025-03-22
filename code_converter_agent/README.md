# SAS to Python Code Converter

A Python-based tool for converting SAS code to equivalent Python code, with a focus on data manipulation and analysis tasks.

## Features

- Converts SAS DATA steps to Pandas operations
- Handles common SAS PROC steps (PRINT, MEANS, FREQ, SORT, etc.)
- Preserves data types and handles SAS-specific formats
- Maintains comments and code structure
- Handles SAS libraries and dataset references

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from sas_to_python_converter import SasToPythonConverter

# Initialize the converter
converter = SasToPythonConverter()

# Convert SAS code
sas_code = """
DATA mydata;
    SET sashelp.class;
    age_plus_1 = age + 1;
RUN;
"""

python_code = converter.convert(sas_code)
print(python_code)
```

## Supported Conversions

### DATA Steps
- Basic data manipulation
- Variable creation and modification
- Dataset merging and concatenation
- Conditional processing (IF-THEN-ELSE)

### PROC Steps
- PRINT → pandas.DataFrame.head/print
- MEANS → pandas.DataFrame.describe
- FREQ → pandas.DataFrame.value_counts
- SORT → pandas.DataFrame.sort_values
- And more...

## Testing

Run the unit tests:

```bash
python -m unittest test_sas_to_python_converter.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 