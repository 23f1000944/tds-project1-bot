from agent import run_agent
import os
from dotenv import load_dotenv

load_dotenv()
res = run_agent("What is the square root of 256? Reply with ONLY a JSON object like {\"answer\": <number>, \"log_url\": \"...\"}")
print(res)
