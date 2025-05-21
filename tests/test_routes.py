import pytest
import os
from io import BytesIO
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"AI Code Quality Analysis Tool" in response.data

def test_analyze_valid_file(client, monkeypatch):
    # Mock analyze_code_with_ai to avoid OpenAI API calls
    def mock_analyze_code_with_ai(code, session_id):
        return {
            "bugs": [],
            "issues_severity": [],
            "optimized_code": code,
            "refactoring_suggestions": []
        }
    monkeypatch.setattr("app.ai_helper.analyze_code_with_ai", mock_analyze_code_with_ai)
    
    # Create a temporary sample.py
    sample_code = 'def example_function(lst):\n    return [x for x in lst]\n'
    with open('sample.py', 'w', encoding='utf-8') as f:
        f.write(sample_code)
    
    try:
        with open('sample.py', 'rb') as f:
            data = {'file': (f, 'sample.py')}
            response = client.post('/analyze', content_type='multipart/form-data', data=data)
            assert response.status_code == 200
            assert b"session_id" in response.data
            assert sample_code.encode() in response.data
            assert b"static_result" in response.data
            assert b"ai_result" in response.data
    finally:
        os.remove('sample.py')

def test_analyze_invalid_file(client):
    data = {'file': (BytesIO(b"not python code"), 'test.txt')}
    response = client.post('/analyze', content_type='multipart/form-data', data=data)
    assert response.status_code == 400
    assert b"Invalid file: Only .py files allowed" in response.data

def test_analyze_code_valid(client, monkeypatch):
    # Mock analyze_code_with_ai
    def mock_analyze_code_with_ai(code, session_id):
        return {
            "bugs": [],
            "issues_severity": [],
            "optimized_code": code,
            "refactoring_suggestions": []
        }
    monkeypatch.setattr("app.ai_helper.analyze_code_with_ai", mock_analyze_code_with_ai)
    
    code = "def test():\n    pass\n"
    response = client.post('/analyze_code', data={'code': code})
    assert response.status_code == 200
    assert b"session_id" in response.data
    assert code.encode() in response.data
    assert b"static_result" in response.data
    assert b"ai_result" in response.data

def test_analyze_code_invalid(client):
    code = "invalid python code"
    response = client.post('/analyze_code', data={'code': code})
    assert response.status_code == 400
    assert b"Invalid Python code" in response.data