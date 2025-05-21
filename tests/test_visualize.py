import pytest
from app.visualize import create_complexity_chart

def test_complexity_chart_valid():
    code = """
def example_function(lst):
    for i in range(len(lst)):
        if lst[i] is None:
            lst[i] = 0
    return lst
"""
    result = create_complexity_chart(code)
    assert "chart_html" in result
    assert "example_function" in result["chart_html"]

def test_complexity_chart_no_functions():
    code = "x = 1"
    result = create_complexity_chart(code)
    assert "error" in result
    assert "No functions found" in result["error"]