from flask import Flask, request
import openai
import os
import telegram
from dotenv import load_dotenv
import requests

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
    
    # Verifica se a mensagem é de voz ou áudio
    if update.message.voice:
        # Baixar o arquivo de áudio
        file_id = update.message.voice.file_id
        file = bot.get_file(file_id)
        file.download('audio.ogg')
        
        # Transcrever o áudio usando o Whisper da OpenAI
        with open('audio.ogg', 'rb') as audio_file:
            transcription = openai.Audio.transcriptions.create(
                model="whisper-1",  # Modelo de transcrição de áudio da OpenAI
                file=audio_file,
                language="pt"
            )
        
        user_message = transcription["text"]
        bot.send_message(chat_id=chat_id, text=f"Texto transcrito: {user_message}")
    
    try:
        # Chamada à API do OpenAI com GPT-4
        completion = openai.ChatCompletion.create(
            model="gpt-4",  # Usando GPT-4
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

