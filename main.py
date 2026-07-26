import os
import json
import uuid
import re
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import FileResponse
import telebot
from telebot import types
from dotenv import load_dotenv
from agent import run_agent

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LLM_API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

app = FastAPI()
bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_sessions = {}

os.makedirs("logs", exist_ok=True)

WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"


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
    match = re.search(r"\{.*\}", text.replace("\n", " "), re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        return {"answer": text}


def process_with_agent(chat_id, user_message):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = []
    history = user_sessions[chat_id][-20:]

    final_answer_str, logs = run_agent(user_message, LLM_API_KEY, chat_history=history)
    user_sessions[chat_id].append(user_message)
    user_sessions[chat_id].append(final_answer_str)
    parsed_answer = extract_json(final_answer_str)

    run_id = str(uuid.uuid4())
    log_filepath = os.path.join("logs", f"{run_id}.jsonl")
    with open(log_filepath, "w") as f:
        for log_entry in logs:
            f.write(json.dumps(log_entry) + "\n")
    log_url = f"{BASE_URL}/{run_id}.jsonl"

    if not isinstance(parsed_answer, dict):
        parsed_answer = {"answer": parsed_answer}
    parsed_answer["log_url"] = log_url

    return parsed_answer


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text
    print(f"Received message from {chat_id}: {text}")
    try:
        response_json = process_with_agent(chat_id, text)
        bot.reply_to(message, json.dumps(response_json))
    except Exception as e:
        run_id = str(uuid.uuid4())
        with open(os.path.join("logs", f"{run_id}.jsonl"), "w") as f:
            f.write(json.dumps({"error": str(e)}) + "\n")
        bot.reply_to(
            message,
            json.dumps({"answer": None, "log_url": f"{BASE_URL}/{run_id}.jsonl"}),
        )


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    update = types.Update.de_json(body)
    background_tasks.add_task(bot.process_new_updates, [update])
    return {"ok": True}


@app.on_event("startup")
def set_webhook():
    webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
    try:
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        print(f"Webhook set to {webhook_url}")
    except Exception as e:
        print(f"WARNING: failed to set webhook: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))