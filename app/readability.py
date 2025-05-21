import json
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.ai_helper import validate_code_content
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_readability_score(code):
    """Evaluate code readability using gpt-4o-mini."""
    validation_result = validate_code_content(code)
    if not validation_result["is_safe"]:
        return {"error": validation_result["message"]}
    
    prompt = (
        "Evaluate the readability and maintainability of the following Python code on a scale of 1-10. "
        "Consider factors like code clarity, structure, naming conventions, and comments. "
        "Return a JSON object with: "
        "'score': An integer from 1 to 10, "
        "'justification': A string explaining the score. "
        "Ensure the response is valid JSON, enclosed in ```json\n...\n```. "
        f"Code: ```\n{code}\n```"
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=500,
            temperature=0.3
        )
        result = response.choices[0].message.content
        print("Readability raw response:", result)  # Debug
        
        # Extract JSON from ```json``` block
        if result.startswith("```json\n") and result.endswith("\n```"):
            result = result[7:-4].strip()
        else:
            return {"error": "AI response not in expected JSON format"}
        
        try:
            parsed_result = json.loads(result)
            return parsed_result
        except json.JSONDecodeError as e:
            print("Readability JSON parsing error:", str(e))
            return {"error": f"Invalid AI response format: {str(e)}"}
    
    except Exception as e:
        print("Readability API error:", str(e))
        return {"error": f"OpenAI API failed: {str(e)}"}