import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import sqlite3
from app.ai_helper import validate_code_content, save_session, load_session, update_session

def test_validate_code_content_safe():
    code = """
def example_function(lst):
    return [0 if x is None else x for x in lst]
"""
    result = validate_code_content(code)
    assert result["is_safe"] is True

def test_validate_code_content_dangerous():
    dangerous_codes = [
        "eval('malicious')",
        "exec('malicious')",
        "import os; os.system('rm -rf /')",
        "import subprocess; subprocess.run(['rm', '-rf', '/'])",
        "__import__('os').system('rm -rf /')"
    ]
    for code in dangerous_codes:
        result = validate_code_content(code)
        assert result["is_safe"] is False
        assert "Potentially harmful code detected" in result["message"]

@pytest.fixture
def db():
    conn = sqlite3.connect(':memory:')
    conn.execute('''
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT,
            original_code TEXT,
            analysis_results TEXT,
            optimized_code TEXT,
            conversation_history TEXT
        )
    ''')
    yield conn
    conn.close()

def test_save_and_load_session(db, monkeypatch):
    def mock_get_db():
        return db
    monkeypatch.setattr("app.ai_helper.get_db", mock_get_db)
    
    session_id = "test-session"
    code = "def test(): pass"
    analysis_results = {"bugs": []}
    optimized_code = "def test(): return None"
    
    save_session(session_id, code, analysis_results, optimized_code)
    session = load_session(session_id)
    
    assert session["session_id"] == session_id
    assert session["original_code"] == code
    assert session["ai_analysis"] == analysis_results
    assert session["optimized_code"] == optimized_code
    assert session["conversation_history"] == []

def test_load_nonexistent_session(db, monkeypatch):
    def mock_get_db():
        return db
    monkeypatch.setattr("app.ai_helper.get_db", mock_get_db)
    
    session = load_session("nonexistent")
    assert session is None