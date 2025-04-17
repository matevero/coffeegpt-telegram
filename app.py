from flask import Flask, request
import requests
from openai import OpenAI
import os
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# Memória por usuário
user_history = {}

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    print("📥 Mensagem recebida:", data)

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_msg = data["message"]["text"]

        # Puxa o histórico ou inicia
        history = user_history.get(chat_id, [])
        history.append({"role": "user", "content": user_msg})

        # Limita o histórico a últimas 10 mensagens (evita custo alto e falhas)
        history = history[-10:]

        try:
            # Adiciona instrução inicial se for nova conversa
            messages = [{"role": "system", "content": "Você é o Zé do Café, um especialista simpático em café e agricultura."}] + history

            chat_completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )

            reply = chat_completion.choices[0].message.content
            print("🤖 Resposta do Zé:", reply)

            # Salva resposta no histórico
            history.append({"role": "assistant", "content": reply})
            user_history[chat_id] = history  # Atualiza

            send_message(chat_id, reply)

        except Exception as e:
            print("❌ Erro:", e)
            send_message(chat_id, "Eita, deu ruim aqui com a cabeça do Zé... tenta de novo depois 😅")

    return "ok", 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


