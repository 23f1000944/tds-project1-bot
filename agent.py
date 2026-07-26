import json
import traceback
import sys
import io
import urllib.request
import os
from google import genai
from google.genai import types

def execute_python_code(code: str) -> str:
    """Executes python code and returns the stdout and stderr."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()
    
    try:
        # Provide some globals
        global_env = {}
        exec(code, global_env)
        stdout_str = redirected_output.getvalue()
        stderr_str = redirected_error.getvalue()
        return f"STDOUT:\n{stdout_str}\nSTDERR:\n{stderr_str}"
    except Exception as e:
        stderr_str = redirected_error.getvalue()
        return f"EXCEPTION:\n{traceback.format_exc()}\nSTDERR:\n{stderr_str}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

def run_agent(question: str, api_key: str, chat_history: list = None):
    """
    Runs the agent with the given question and history.
    chat_history should be a list of strings if we want to include previous turns.
    Returns (final_answer_json_str, logs_list)
    """
    client = genai.Client(api_key=api_key)
    
    system_instruction = (
        "You are a Data Analyst Agent. Your goal is to answer data-analysis questions. "
        "You can execute Python code to download data, read CSVs/JSONs, and perform analysis. "
        "When you use the execute_python_code tool, print the final answer so you can see it in the STDOUT. "
        "Once you have the answer, you must respond with EXACTLY ONE JSON OBJECT containing the answer "
        "in the exact shape requested by the user. DO NOT wrap the JSON in markdown blocks like ```json. "
        "Just output the raw JSON object."
    )
    
    # We will manually manage the chat loop to record logs
    messages = []
    
    if chat_history:
        for msg in chat_history:
            messages.append(types.Content(role="user", parts=[types.Part.from_text(text=msg)]))
            # Assuming history is all user messages for now, or you can format them
    
    messages.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))
    
    logs = []
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[execute_python_code],
        temperature=0.0
    )
    
    max_steps = 5
    for step in range(max_steps):
        # Generate content
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=messages,
            config=config
        )
        
        # Log the response
        logs.append({
            "step": step,
            "role": "model",
            "content": response.text,
            "function_calls": [fc.name for fc in (response.function_calls or [])]
        })
        
        # Add model response to messages
        if response.candidates and response.candidates[0].content:
            messages.append(response.candidates[0].content)
        else:
            break
            
        if response.function_calls:
            for function_call in response.function_calls:
                if function_call.name == "execute_python_code":
                    code = function_call.args.get('code', '')
                    logs.append({
                        "step": step,
                        "action": "execute_python_code",
                        "code": code
                    })
                    
                    print("Executing code:\n", code)
                    result = execute_python_code(code)
                    
                    logs.append({
                        "step": step,
                        "action": "execute_python_code_result",
                        "result": result
                    })
                    
                    # Add function response to messages
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_function_response(
                                name="execute_python_code",
                                response={"result": result}
                            )]
                        )
                    )
        else:
            # No function calls, so this is the final answer
            break
            
    # The final text from the model should be the JSON object
    final_text = response.text
    if final_text.startswith("```json"):
        final_text = final_text[7:]
    if final_text.startswith("```"):
        final_text = final_text[3:]
    if final_text.endswith("```"):
        final_text = final_text[:-3]
        
    return final_text.strip(), logs
