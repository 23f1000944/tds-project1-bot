import os
from google import genai
client = genai.Client(api_key=os.environ['LLM_API_KEY'])
import time

for m in ['gemini-flash-latest', 'gemini-3.5-flash']:
    print(f"Testing {m}...")
    try:
        for i in range(20):
            client.models.generate_content(model=m, contents="hi")
        print(f"{m} allows at least 20 requests!")
    except Exception as e:
        print(f"{m} error after some requests: {e}")
    time.sleep(2)
