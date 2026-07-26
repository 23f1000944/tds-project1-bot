import os
import json
from google import genai
client = genai.Client(api_key=os.environ['LLM_API_KEY'])
models_to_test = ['gemini-flash-latest', 'gemini-3.5-flash', 'gemini-3.6-flash']
for m in models_to_test:
    try:
        response = client.models.generate_content(
            model=m,
            contents="Say hi"
        )
        print(f"{m}: OK")
    except Exception as e:
        print(f"{m}: ERROR {e}")
