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

# URL do webhook (substitua pelo seu domínio real)
webhook_url = f"https://coffeegpt-telegram.onrender.com/{7105411303:AAFgfzIZAVEYSl7DEyeoZBsB-zaG8t3YhR4}"

# Configura o webhook
bot.set_webhook(url=webhook_url)

app = Flask(__name__)

@app.route("/check_webhook", methods=["GET"])
def check_webhook():
    try:
        webhook_info = bot.get_webhook_info()
        return f"Informações do Webhook: {webhook_info}"
    except Exception as e:
        return f"Erro ao verificar o webhook: {e}"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def respond():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    user_message = update.message.text

    try:
        # Chamada à API do OpenAI
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
        # Enviar mensagem caso ocorra erro
        bot.send_message(chat_id=chat_id, text="Eita, deu ruim aqui na mente do CoffeeGPT 😅")
        print("Erro:", e)

    return "ok"

@app.route("/webhook", methods=["GET"])
def webhook_status():
    return "Webhook está funcionando!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
