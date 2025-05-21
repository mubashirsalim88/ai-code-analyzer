from flask import Blueprint, render_template, request, jsonify, current_app, make_response
import os
import uuid
import ast
import json
import inspect
import importlib
from app.analyzer import analyze_code_static
from app.readability import get_readability_score
from app.visualize import create_complexity_chart
from app.ai_helper import analyze_code_with_ai, regenerate_code, load_session

routes = Blueprint('routes', __name__)

# Debug: Verify analyze_code_static at import
print(f"analyze_code_static module: {analyze_code_static.__module__}")
print(f"analyze_code_static file: {inspect.getfile(analyze_code_static)}")
print(f"analyze_code_static signature: {inspect.signature(analyze_code_static)}")

def validate_python_file(file_path):
    """Validate that the file contains valid Python code."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        return True
    except SyntaxError:
        return False

def validate_python_code(code):
    """Validate that the code is valid Python."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False

@routes.route('/')
def index():
    """Render the home page with file upload and chat interface."""
    return render_template('index.html', session_id=None)

@routes.route('/debug_templates')
def debug_templates():
    """List available templates for debugging."""
    templates = current_app.jinja_env.list_templates()
    return jsonify({"available_templates": templates})

@routes.route('/analyze', methods=['POST'])
def analyze():
    """Handle file upload, run static and AI analysis, and create session."""
    file = request.files.get('file')
    if not file or not file.filename.endswith('.py'):
        return jsonify({"error": "Invalid file: Only .py files allowed"}), 400
    if file.content_length > 5 * 1024 * 1024:  # 5MB limit
        return jsonify({"error": "File too large (max 5MB)"}), 400
    
    # Save file
    session_id = str(uuid.uuid4())
    file_path = os.path.join('Uploads', f"{session_id}.py")
    file.save(file_path)
    
    if not validate_python_file(file_path):
        os.remove(file_path)
        return jsonify({"error": "Invalid Python code"}), 400
    
    # Read code
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Debug: Verify analyze_code_static before call
    importlib.reload(importlib.import_module('app.analyzer'))
    from app.analyzer import analyze_code_static
    print(f"Runtime analyze_code_static signature: {inspect.signature(analyze_code_static)}")
    
    # Run static analysis
    static_result = analyze_code_static(code)
    if "error" in static_result:
        os.remove(file_path)
        return jsonify(static_result), 400
    
    # Run AI analysis
    ai_result = analyze_code_with_ai(code, session_id)
    if "error" in ai_result:
        os.remove(file_path)
        return jsonify(ai_result), 400
    
    # Run readability analysis
    readability_result = get_readability_score(code)
    if "error" in readability_result:
        readability_result = {"score": 0, "justification": "Readability analysis failed"}
    
    # Run complexity visualization
    complexity_chart = create_complexity_chart(code)
    if "error" in complexity_chart:
        complexity_chart = {"chart_html": "<p>No complexity chart available</p>"}
    
    # Prepare AI analysis for rendering
    ai_result_render = {
        "bugs": ai_result.get("bugs", []),
        "issues_severity": ai_result.get("issues_severity", []),
        "optimized_code": ai_result.get("optimized_code", code),
        "refactoring_suggestions": [
            {
                "description": sug["description"],
                "example_code": sug.get("example_code", "")
            }
            for sug in ai_result.get("refactoring_suggestions", [])
        ]
    }
    
    # Render results with session ID and original code
    return render_template(
        'index.html',
        session_id=session_id,
        static_result=static_result,
        ai_result=ai_result_render,
        readability_result=readability_result,
        complexity_chart=complexity_chart,
        original_code=code
    )

@routes.route('/analyze_code', methods=['POST'])
def analyze_code():
    """Handle code input from text editor, run analysis, and create session."""
    code = request.form.get('code')
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    if not validate_python_code(code):
        return jsonify({"error": "Invalid Python code"}), 400
    
    # Save code to a temporary file
    session_id = str(uuid.uuid4())
    file_path = os.path.join('Uploads', f"{session_id}.py")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    # Debug: Verify analyze_code_static before call
    importlib.reload(importlib.import_module('app.analyzer'))
    from app.analyzer import analyze_code_static
    print(f"Runtime analyze_code_static signature: {inspect.signature(analyze_code_static)}")
    
    # Run static analysis
    static_result = analyze_code_static(code)
    if "error" in static_result:
        os.remove(file_path)
        return jsonify(static_result), 400
    
    # Run AI analysis
    ai_result = analyze_code_with_ai(code, session_id)
    if "error" in ai_result:
        os.remove(file_path)
        return jsonify(ai_result), 400
    
    # Run readability analysis
    readability_result = get_readability_score(code)
    if "error" in readability_result:
        readability_result = {"score": 0, "justification": "Readability analysis failed"}
    
    # Run complexity visualization
    complexity_chart = create_complexity_chart(code)
    if "error" in complexity_chart:
        complexity_chart = {"chart_html": "<p>No complexity chart available</p>"}
    
    # Prepare AI analysis for rendering
    ai_result_render = {
        "bugs": ai_result.get("bugs", []),
        "issues_severity": ai_result.get("issues_severity", []),
        "optimized_code": ai_result.get("optimized_code", code),
        "refactoring_suggestions": [
            {
                "description": sug["description"],
                "example_code": sug.get("example_code", "")
            }
            for sug in ai_result.get("refactoring_suggestions", [])
        ]
    }
    
    # Render results with session ID and original code
    return render_template(
        'index.html',
        session_id=session_id,
        static_result=static_result,
        ai_result=ai_result_render,
        readability_result=readability_result,
        complexity_chart=complexity_chart,
        original_code=code
    )

@routes.route('/export/<session_id>')
def export_analysis(session_id):
    """Export analysis results as JSON."""
    session = load_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    # Debug: Verify analyze_code_static before call
    importlib.reload(importlib.import_module('app.analyzer'))
    from app.analyzer import analyze_code_static
    print(f"Runtime analyze_code_static signature: {inspect.signature(analyze_code_static)}")
    
    # Use stored data to avoid re-running AI analysis
    code = session["original_code"]
    static_result = analyze_code_static(code)
    ai_result = session.get("ai_analysis", {})
    readability_result = get_readability_score(code)
    complexity_chart = create_complexity_chart(code)
    
    export_data = {
        "original_code": code,
        "static_analysis": static_result,
        "ai_analysis": ai_result,
        "readability_analysis": readability_result,
        "complexity_chart": {
            "functions": complexity_chart.get("functions", []),
            "module_complexity": complexity_chart.get("module_complexity", 0)
        }
    }
    
    response = make_response(json.dumps(export_data, indent=2))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=analysis_{session_id}.json'
    return response

@routes.route('/regenerate', methods=['POST'])
def regenerate():
    """Handle user commands to regenerate optimized code."""
    session_id = request.form.get('session_id')
    user_command = request.form.get('user_command')
    if not session_id or not user_command:
        return jsonify({"error": "Missing session_id or command"}), 400
    
    result = regenerate_code(session_id, user_command)
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify({"response": result})