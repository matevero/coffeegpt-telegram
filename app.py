from flask import Flask, request
import requests
from openai import OpenAI
import os
import psycopg2
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# Conexão com o PostgreSQL
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Cria a tabela se não existir
cursor.execute("""
    CREATE TABLE IF NOT EXISTS memoria (
        chat_id BIGINT PRIMARY KEY,
        historico TEXT
    );
""")
conn.commit()

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    print("📥 Mensagem recebida:", data)

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_msg = data["message"]["text"]

        # Recupera histórico
        cursor.execute("SELECT historico FROM memoria WHERE chat_id = %s", (chat_id,))
        result = cursor.fetchone()
        historico = result[0] if result else ""

        messages = [
            {"role": "system", "content": "Você é o Zé do Café, um especialista simpático em café e agricultura."}
        ]

        if historico:
            messages.append({"role": "user", "content": historico})

        messages.append({"role": "user", "content": user_msg})

        try:
            chat_completion = client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )

            reply = chat_completion.choices[0].message.content
            print("🤖 Resposta do Zé:", reply)

            # Atualiza histórico no banco
            novo_historico = historico + "\n" + user_msg + "\n" + reply
            cursor.execute("""
                INSERT INTO memoria (chat_id, historico)
                VALUES (%s, %s)
                ON CONFLICT (chat_id)
                DO UPDATE SET historico = EXCLUDED.historico;
            """, (chat_id, novo_historico))
            conn.commit()

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



