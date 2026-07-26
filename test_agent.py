from bot import process_with_agent
import json
import time

def test_agent():
    chat_id = 12345
    print("Testing single-turn question...")
    question = "Which state has the highest maternal mortality rate based on MOSPI data? Reply with ONLY this JSON object and nothing else: {\"answer\": {\"state\": \"<state name>\"}}"
    
    start_time = time.time()
    response = process_with_agent(chat_id, question)
    end_time = time.time()
    
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print("Agent Response:")
    print(json.dumps(response, indent=2))
    
    if "log_url" in response and "answer" in response:
        print("✅ SUCCESS: Response has correct shape")
    else:
        print("❌ ERROR: Response shape is incorrect")

if __name__ == "__main__":
    test_agent()
