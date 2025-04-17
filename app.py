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

# Função para configurar o webhook do Telegram
def set_webhook():
    webhook_url = f"https://coffeegpt-telegram.onrender.com/{TELEGRAM_TOKEN}"  # URL do webhook do seu bot
    set_webhook_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}"

    response = requests.get(set_webhook_url)
    if response.status_code == 200:
        print("Webhook configurado com sucesso!")
    else:
        print(f"Erro ao configurar o webhook: {response.text}")

# Configurando o webhook assim que a aplicação iniciar
set_webhook()

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def respond():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    user_message = update.message.text

    # Log da mensagem recebida
    print(f"Mensagem recebida: {user_message}")

    try:
        # Chamada à API de chat da OpenAI
        response = openai.chat_completions.create(
            model="gpt-3.5-turbo",  # Modelo do chat
            messages=[
                {"role": "system", "content": "Você é o CoffeeGPT, um assistente simpático para produtores de café."},
                {"role": "user", "content": user_message}
            ]
        )

        # Log da resposta da OpenAI
        print("Resposta recebida da OpenAI:", response)

        # Obter a resposta do modelo
        response_text = response['choices'][0]['message']['content']
        bot.send_message(chat_id=chat_id, text=response_text)

    except Exception as e:
        # Log detalhado do erro
        error_message = f"Erro: {str(e)}\n{traceback.format_exc()}"
        bot.send_message(chat_id=chat_id, text="Eita, deu ruim aqui na mente do CoffeeGPT 😅")
        print("Erro detalhado:", error_message)

    return "ok"

@app.route("/webhook", methods=["GET"])
def webhook_status():
    return "Webhook está funcionando!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

