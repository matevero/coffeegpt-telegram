from flask import Flask, request
import openai
import os
import telegram
from dotenv import load_dotenv
import requests
import traceback

# Carrega variáveis do .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telegram.Bot(token=TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

# Configura automaticamente o webhook do Telegram
def set_webhook():
    webhook_url = f"https://coffeegpt-telegram.onrender.com/{TELEGRAM_TOKEN}"
    response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}")
    if response.status_code == 200:
        print("✅ Webhook configurado com sucesso!")
    else:
        print(f"❌ Erro ao configurar o webhook: {response.text}")

set_webhook()

@app.route("/", methods=["GET"])
def index():
    return "CoffeeGPT está online!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def respond():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    user_message = update.message.text

    print(f"📥 Mensagem recebida: {user_message}")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[

