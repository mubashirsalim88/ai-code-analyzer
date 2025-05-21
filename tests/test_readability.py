import pytest
from app.readability import get_readability_score
from unittest.mock import patch

def test_readability_valid():
    code = """
def example_function(lst):
    for i in range(len(lst)):
        if lst[i] is None:
            lst[i] = 0
    return lst
"""
    with patch("app.readability.client.chat.completions.create") as mock_create:
        mock_create.return_value.choices = [
            type("obj", (), {"message": type("obj", (), {"content": """```json
{
    "score": 6,
    "justification": "Readable but could use better naming."
}
```"""})})
        ]
        result = get_readability_score(code)
        assert "score" in result
        assert result["score"] == 6
        assert "justification" in result

def test_readability_invalid_content():
    code = "eval('malicious')"
    result = get_readability_score(code)
    assert "error" in result
    assert "Invalid code content" in result["error"]