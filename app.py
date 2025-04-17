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

# Rota para verificar o status do webhook
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        chat_id = update.message.chat.id
        user_message = update.message.text
        
        # Processar mensagem de áudio
        if update.message.voice:
            # Baixar e transcrever o áudio
            file_id = update.message.voice.file_id
            file = bot.get_file(file_id)
            file.download('audio.ogg')
            
            # Transcrever com o Whisper da OpenAI
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
            bot.send_message(chat_id=chat_id, text="Eita, deu ruim aqui na mente do CoffeeGPT 😅")
            print("Erro:", e)

        return "ok"
    
    return "Webhook está funcionando!"

# Rota opcional para verificar o status do webhook
@app.route("/check_webhook", methods=["GET"])
def check_webhook():
    try:
        webhook_info = bot.get_webhook_info()
        return f"Informações do Webhook: {webhook_info}"
    except Exception as e:
        return f"Erro ao verificar o webhook: {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

