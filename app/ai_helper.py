import os
import json
import sqlite3
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

load_dotenv()

# Debug: Print environment variables
print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))
print("HTTP_PROXY:", os.getenv("HTTP_PROXY"))
print("HTTPS_PROXY:", os.getenv("HTTPS_PROXY"))

# Initialize OpenAI client with minimal arguments
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print("OpenAI client initialized successfully")
except Exception as e:
    print("OpenAI client initialization failed:", str(e))
    raise

def get_db():
    """Get SQLite database connection."""
    conn = sqlite3.connect('logs/analyzer.db')
    conn.row_factory = sqlite3.Row
    return conn

def validate_code_content(code):
    """Check for potentially harmful code."""
    dangerous_patterns = [
        "eval(",
        "exec(",
        "os.system(",
        "subprocess.run(",
        "subprocess.call(",
        "subprocess.Popen(",
        "__import__('os').system(",
        "__import__('subprocess')."
    ]
    for pattern in dangerous_patterns:
        if pattern in code:
            return {"is_safe": False, "message": f"Potentially harmful code detected: {pattern}"}
    return {"is_safe": True}

def save_session(session_id, original_code, analysis_results, optimized_code):
    """Save session data to SQLite."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT,
            original_code TEXT,
            analysis_results TEXT,
            optimized_code TEXT,
            conversation_history TEXT
        )
        """
    )
    cursor.execute(
        """
        INSERT OR REPLACE INTO sessions (session_id, created_at, original_code, analysis_results, optimized_code, conversation_history)
        VALUES (?, datetime('now'), ?, ?, ?, ?)
        """,
        (session_id, original_code, json.dumps(analysis_results), optimized_code, json.dumps([]))
    )
    conn.commit()
    conn.close()

def load_session(session_id):
    """Load session data from SQLite."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "session_id": result["session_id"],
            "original_code": result["original_code"],
            "ai_analysis": json.loads(result["analysis_results"]),
            "optimized_code": result["optimized_code"],
            "conversation_history": json.loads(result["conversation_history"])
        }
    return None

def update_session(session_id, new_optimized_code, user_command):
    """Update session with new optimized code and conversation history."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT conversation_history FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    history = json.loads(row["conversation_history"])
    history.append({"user_command": user_command, "response": new_optimized_code})
    cursor.execute(
        "UPDATE sessions SET optimized_code = ?, conversation_history = ? WHERE session_id = ?",
        (new_optimized_code, json.dumps(history), session_id)
    )
    conn.commit()
    conn.close()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def analyze_code_with_ai(code, session_id):
    """Analyze code using OpenAI's gpt-4o-mini."""
    validation_result = validate_code_content(code)
    if not validation_result["is_safe"]:
        return {"error": validation_result["message"]}
    
    prompt = (
        "You are a Python code analysis assistant. Analyze the following Python code for potential bugs, maintenance issues, and refactoring opportunities. "
        "Return a JSON object with the following fields: "
        "1. 'bugs': A list of objects with 'line_number', 'description', and 'severity' (high, medium, low). "
        "2. 'refactoring_suggestions': A list of objects with 'description' and 'example_code'. "
        "3. 'optimized_code': A string containing the optimized version of the code. "
        "4. 'issues_severity': A list of objects with 'issue' and 'severity'. "
        "Ensure the response is valid JSON, enclosed in ```json\n...\n```. Do not include additional text outside the JSON. "
        f"Code: ```\n{code}\n```"
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        result = response.choices[0].message.content
        print("Raw OpenAI response:", result)  # Debug
        
        # Extract JSON from ```json``` block
        if result.startswith("```json\n") and result.endswith("\n```"):
            result = result[7:-4].strip()
        else:
            return {"error": "AI response not in expected JSON format"}
        
        try:
            parsed_result = json.loads(result)
        except json.JSONDecodeError as e:
            print("JSON parsing error:", str(e))
            return {"error": f"Invalid AI response format: {str(e)}"}
        
        optimized_code = parsed_result.get("optimized_code", code)
        save_session(session_id, code, parsed_result, optimized_code)
        return parsed_result
    
    except Exception as e:
        print("OpenAI API error:", str(e))
        return {"error": f"OpenAI API failed: {str(e)}"}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def regenerate_code(session_id, user_command):
    """Regenerate optimized code based on user command."""
    session = load_session(session_id)
    if not session:
        return {"error": "Session not found"}
    
    original_code = session["original_code"]
    optimized_code = session["optimized_code"]
    history = session["conversation_history"]
    
    prompt = (
        f"You are a Python code optimization assistant. "
        f"Original code: ```\n{original_code}\n```. "
        f"Previous optimized code: ```\n{optimized_code}\n```. "
        f"Conversation history: {json.dumps(history)}. "
        f"User request: '{user_command}'. "
        "Return a JSON object with: "
        "'optimized_code': The updated optimized code, "
        "'explanation': A string explaining the changes. "
        "Ensure the response is valid JSON, enclosed in ```json\n...\n```."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=1500,
            temperature=0.3
        )
        result = response.choices[0].message.content
        print("Raw OpenAI response (regenerate):", result)  # Debug
        
        # Extract JSON from ```json``` block
        if result.startswith("```json\n") and result.endswith("\n```"):
            result = result[7:-4].strip()
        else:
            return {"error": "AI response not in expected JSON format"}
        
        try:
            parsed_result = json.loads(result)
            new_optimized_code = parsed_result.get("optimized_code", optimized_code)
            update_session(session_id, new_optimized_code, user_command)
            return parsed_result
        except json.JSONDecodeError as e:
            print("JSON parsing error (regenerate):", str(e))
            return {"error": f"Invalid AI response format: {str(e)}"}
    
    except Exception as e:
        print("OpenAI API error (regenerate):", str(e))
        return {"error": f"OpenAI API failed: {str(e)}"}