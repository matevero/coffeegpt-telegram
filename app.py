from flask import Flask, request
import openai
import os
import telegram
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
bot = telegram.Bot(token=TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def respond():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    user_message = update.message.text

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é o CoffeeGPT, um assistente simpático para produtores de café."},
                {"role": "user", "content": user_message}
            ]
        )
        response_text = completion.choices[0].message.content
        bot.send_message(chat_id=chat_id, text=response_text)

    except Exception as e:
        bot.send_message(chat_id=chat_id, text="Eita, deu ruim aqui na mente do CoffeeGPT 😅")
        print("Erro:", e)

    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "CoffeeGPT está no ar!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
