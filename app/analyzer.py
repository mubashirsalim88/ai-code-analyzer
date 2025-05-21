import ast
from flake8.api import legacy as flake8
import radon.complexity as radon_cc
import radon.metrics as radon_metrics
import json
import os
import tempfile
import subprocess

def analyze_code_static(code):
    """Perform static analysis on Python code."""
    try:
        # Validate syntax
        ast.parse(code)
    except SyntaxError as e:
        return {"error": f"Invalid Python code: {str(e)}"}
    
    # Ensure code ends with a newline
    if not code.endswith('\n'):
        code += '\n'
    
    # Temporary file for analysis
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w', encoding='utf-8') as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name
    print("Temp file path:", temp_file_path)  # Debug
    
    result = {"complexity": {}, "style_issues": [], "warnings": []}
    
    # Pylint analysis
    try:
        pylint_version = subprocess.run(['pylint', '--version'], capture_output=True, text=True, check=True)
        print("Pylint version:", pylint_version.stdout)  # Debug
        
        pylint_cmd = ['pylint', '--output-format=json', '--disable=invalid-name', temp_file_path]
        pylint_result = subprocess.run(pylint_cmd, capture_output=True, text=True)
        pylint_raw_output = pylint_result.stdout
        print("Pylint raw output:", pylint_raw_output)  # Debug
        print("Pylint stderr:", pylint_result.stderr)  # Debug
        
        if pylint_result.returncode & 32:
            result["warnings"].append({"line": 0, "message": f"Pylint failed with exit code {pylint_result.returncode}: {pylint_result.stderr}"})
        elif not pylint_raw_output.strip():
            result["warnings"].append({"line": 0, "message": "Pylint produced no output"})
        else:
            try:
                pylint_issues = json.loads(pylint_raw_output)
                style_issues = [
                    {"line": issue["line"], "message": issue["message"]}
                    for issue in pylint_issues
                ]
                result["style_issues"].extend(style_issues)
                result["warnings"].extend(style_issues)
            except json.JSONDecodeError as e:
                result["warnings"].append({"line": 0, "message": f"Pylint output invalid JSON: {str(e)}"})
    except subprocess.CalledProcessError as e:
        result["warnings"].append({"line": 0, "message": f"Pylint subprocess failed: {str(e)}"})
    except Exception as e:
        result["warnings"].append({"line": 0, "message": f"Pylint failed: {str(e)}"})
    
    # Flake8 analysis
    try:
        flake8_style = flake8.get_style_guide()
        flake8_report = flake8_style.check_files([temp_file_path])
        flake8_issues = [
            {"line": error.line_number, "message": error.text}
            for error in flake8_report.get_statistics('E')
        ]
        result["style_issues"].extend(flake8_issues)
        result["warnings"].extend(flake8_issues)
    except Exception as e:
        result["warnings"].append({"line": 0, "message": f"Flake8 failed: {str(e)}"})
    
    # Radon complexity analysis
    try:
        cc_results = radon_cc.cc_visit(code)
        result["complexity"] = {
            "functions": [
                {"name": block.name, "complexity": block.complexity}
                for block in cc_results
                if block.classname is None  # Exclude classes
            ],
            "module_complexity": sum(block.complexity for block in cc_results)
        }
    except Exception as e:
        result["warnings"].append({"line": 0, "message": f"Radon failed: {str(e)}"})
    
    # Clean up
    try:
        os.remove(temp_file_path)
    except OSError:
        pass
    
    return result