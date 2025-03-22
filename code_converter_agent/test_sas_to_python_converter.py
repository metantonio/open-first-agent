import unittest
import asyncio
from agents import Runner
from .code_converter_agent import (
    run_workflow,
    code_converter_orchestrator,
    data_step_converter,
    proc_converter,
    macro_converter
)

class TestCodeConverterAgents(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()

    def test_data_step_converter(self):
        """Test DATA step conversion agent."""
        sas_code = """
        DATA mydata;
            SET sashelp.class;
            age_plus_1 = age + 1;
            height_m = height * 2.54;
        RUN;
        """
        
        result = self.loop.run_until_complete(Runner.run(
            data_step_converter,
            sas_code
        ))
        
        self.assertIsNotNone(result)
        python_code = result.final_output
        self.assertIn('import pandas as pd', python_code)
        self.assertIn('mydata = sashelp.class.copy()', python_code)
        self.assertIn('age_plus_1 = age + 1', python_code)
        self.assertIn('height_m = height * 2.54', python_code)

    def test_proc_converter(self):
        """Test PROC step conversion agent."""
        test_cases = [
            {
                'sas': "PROC MEANS DATA=sashelp.class;RUN;",
                'expected_func': 'describe()'
            },
            {
                'sas': "PROC PRINT DATA=sashelp.class;RUN;",
                'expected_func': 'head()'
            },
            {
                'sas': "PROC FREQ DATA=sashelp.class;RUN;",
                'expected_func': 'value_counts()'
            }
        ]
        
        for case in test_cases:
            result = self.loop.run_until_complete(Runner.run(
                proc_converter,
                case['sas']
            ))
            
            self.assertIsNotNone(result)
            python_code = result.final_output
            self.assertIn('import pandas as pd', python_code)
            self.assertIn(case['expected_func'], python_code)

    def test_macro_converter(self):
        """Test macro conversion agent."""
        sas_code = """
        %MACRO calculate_stats(var, dataset);
            PROC MEANS DATA=&dataset;
                VAR &var;
            RUN;
        %MEND;
        """
        
        result = self.loop.run_until_complete(Runner.run(
            macro_converter,
            sas_code
        ))
        
        self.assertIsNotNone(result)
        python_code = result.final_output
        self.assertIn('def calculate_stats(var, dataset):', python_code)

    def test_orchestrator_data_step(self):
        """Test orchestrator handling of DATA step."""
        sas_code = """
        DATA mydata;
            SET sashelp.class;
            age_plus_1 = age + 1;
        RUN;
        """
        
        result = run_workflow(sas_code)
        self.assertIsInstance(result, str)
        self.assertIn('import pandas as pd', result)
        self.assertIn('mydata = sashelp.class.copy()', result)

    def test_orchestrator_proc_step(self):
        """Test orchestrator handling of PROC step."""
        sas_code = "PROC MEANS DATA=sashelp.class;RUN;"
        
        result = run_workflow(sas_code)
        self.assertIsInstance(result, str)
        self.assertIn('import pandas as pd', result)
        self.assertIn('describe()', result)

    def test_orchestrator_macro(self):
        """Test orchestrator handling of macro."""
        sas_code = """
        %MACRO calculate_mean(var);
            PROC MEANS DATA=&dataset;
                VAR &var;
            RUN;
        %MEND;
        """
        
        result = run_workflow(sas_code)
        self.assertIsInstance(result, str)
        self.assertIn('def calculate_mean', result)

    def test_orchestrator_complex_code(self):
        """Test orchestrator handling of complex SAS code with multiple components."""
        sas_code = """
        %MACRO process_data(var);
            DATA temp;
                SET sashelp.class;
                new_var = &var + 10;
            RUN;
            
            PROC MEANS DATA=temp;
                VAR new_var;
            RUN;
        %MEND;
        
        DATA mydata;
            SET sashelp.class;
            age_plus_1 = age + 1;
        RUN;
        
        PROC PRINT DATA=mydata;RUN;
        """
        
        result = run_workflow(sas_code)
        self.assertIsInstance(result, str)
        self.assertIn('def process_data', result)
        self.assertIn('sashelp.class', result)
        self.assertIn('age_plus_1', result)
        self.assertIn('head()', result)

    def test_error_handling(self):
        """Test error handling in conversion process."""
        # Test invalid DATA step
        invalid_data = "DATA;"
        result = run_workflow(invalid_data)
        self.assertIn('error', result.lower())
        
        # Test invalid PROC step
        invalid_proc = "PROC INVALID;"
        result = run_workflow(invalid_proc)
        self.assertIn('error', result.lower())
        
        # Test invalid macro
        invalid_macro = "%MACRO;"
        result = run_workflow(invalid_macro)
        self.assertIn('error', result.lower())

    def test_quoted_strings_handling(self):
        """Test handling of quoted strings with semicolons."""
        sas_code = """
        DATA mydata;
            string_var = "Hello; World";
            another_var = 'Contains; semicolon';
        RUN;
        """
        
        result = self.loop.run_until_complete(Runner.run(
            data_step_converter,
            sas_code
        ))
        
        self.assertIsNotNone(result)
        python_code = result.final_output
        self.assertIn('string_var = "Hello; World"', python_code)
        self.assertIn("another_var = 'Contains; semicolon'", python_code)

if __name__ == '__main__':
    unittest.main() 