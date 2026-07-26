import os
import json
import threading
import time
import uuid
import re
from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn
import telebot
from dotenv import load_dotenv
from agent import run_agent

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LLM_API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://tds-project1-bot.onrender.com")

app = FastAPI()
bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_sessions = {}

os.makedirs("logs", exist_ok=True)

@app.get("/health")
def health_check():
    return {"ok": True, "status": "running"}

@app.get("/{filename}.jsonl")
def get_log(filename: str):
    path = os.path.join("logs", f"{filename}.jsonl")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "File not found"}

def extract_json(text):
    # Try to find the first balanced { ... } block
    match = re.search(r'\{.*\}', text.replace('\n', ' '), re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    try:
        return json.loads(text)
    except:
        return {"answer": text}

def process_with_agent(chat_id, user_message):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = []
        
    history = user_sessions[chat_id][-20:] # Keep last 20 messages for context
    
    # Run the agent
    final_answer_str, logs = run_agent(user_message, LLM_API_KEY, chat_history=history)
    
    user_sessions[chat_id].append(user_message)
    user_sessions[chat_id].append(final_answer_str)
    
    parsed_answer = extract_json(final_answer_str)
        
    run_id = str(uuid.uuid4())
    log_filename = f"{run_id}.jsonl"
    log_filepath = os.path.join("logs", log_filename)
    
    with open(log_filepath, "w") as f:
        for log_entry in logs:
            f.write(json.dumps(log_entry) + "\n")
            
    log_url = f"{BASE_URL}/{run_id}.jsonl"
    
    # The guide says "Always overwrite log_url with your real URL"
    if "log_url" in parsed_answer:
        parsed_answer["log_url"] = log_url
    # If the user asked for it but the LLM missed it:
    elif "log_url" in user_message.lower():
        parsed_answer["log_url"] = log_url
        
    return parsed_answer

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text
    
    try:
        response_json = process_with_agent(chat_id, text)
        bot.reply_to(message, json.dumps(response_json))
    except Exception as e:
        # Never crash silently
        run_id = str(uuid.uuid4())
        with open(os.path.join("logs", f"{run_id}.jsonl"), "w") as f:
            f.write(json.dumps({"error": str(e)}) + "\n")
        bot.reply_to(message, json.dumps({"answer": "internal error", "log_url": f"{BASE_URL}/{run_id}.jsonl"}))

def run_bot():
    print("Starting Telegram Bot...")
    bot.infinity_polling()

@app.on_event("startup")
def startup_event():
    # Start bot in a background thread
    threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
