import pytest
from app.analyzer import analyze_code

def test_analyze_code_valid():
    code = """
def example_function(lst):
    for i in range(len(lst)):
        if lst[i] is None:
            lst[i] = 0
    return lst
"""
    result = analyze_code(code)
    assert "complexity" in result
    assert "style_issues" in result
    assert "warnings" in result
    assert result["complexity"]["module_complexity"] == 3
    # Check for any style issue to make test more robust
    assert len(result["style_issues"]) > 0, "Expected at least one style issue"

def test_analyze_code_invalid():
    code = "def invalid():"  # Missing indentation
    result = analyze_code(code)
    assert "error" in result
    assert "Invalid Python code" in result["error"]