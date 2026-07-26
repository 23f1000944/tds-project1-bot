import os
import json
import telebot
from dotenv import load_dotenv
from agent import run_agent
import uuid

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LLM_API_KEY = os.getenv("LLM_API_KEY")
# The public URL where the logs will be accessible
LOGS_BASE_URL = os.getenv("LOGS_BASE_URL", "http://localhost:8000")

if not TELEGRAM_TOKEN or not LLM_API_KEY:
    print("Please set TELEGRAM_TOKEN and LLM_API_KEY in your .env file.")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# In-memory storage for multi-turn conversations
user_sessions = {}
# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

def process_with_agent(chat_id, user_message):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = []
        
    history = user_sessions[chat_id]
    
    # Run the agent
    final_answer_str, logs = run_agent(user_message, LLM_API_KEY, chat_history=history)
    
    # Append to history
    user_sessions[chat_id].append(user_message)
    user_sessions[chat_id].append(final_answer_str)
    
    # Try to parse the final answer as JSON
    try:
        parsed_answer = json.loads(final_answer_str)
    except Exception as e:
        # If it failed to parse, maybe we wrap it
        parsed_answer = {"error": "LLM did not return valid JSON", "raw": final_answer_str}
        
    # Save logs to a JSONL file
    run_id = str(uuid.uuid4())
    log_filename = f"{run_id}.jsonl"
    log_filepath = os.path.join("logs", log_filename)
    
    with open(log_filepath, "w") as f:
        for log_entry in logs:
            f.write(json.dumps(log_entry) + "\n")
            
    log_url = f"{LOGS_BASE_URL}/{log_filename}"
    
    if isinstance(parsed_answer, dict):
        return parsed_answer
    else:
        return {"answer": parsed_answer}

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text
    
    print(f"Received message from {chat_id}: {text}")
    
    try:
        # Process the message with the agent
        response_json = process_with_agent(chat_id, text)
        
        # Reply with ONLY the JSON object
        bot.reply_to(message, json.dumps(response_json))
    except Exception as e:
        print(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()
        bot.reply_to(message, json.dumps({"error": str(e)}))

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
