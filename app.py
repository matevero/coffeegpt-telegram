from flask import Flask, request
import requests
import sqlite3
from openai import OpenAI
import os
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Inicializa o banco de dados SQLite
def init_db():
    conn = sqlite3.connect('memory.db')
    c = conn.cursor()
    # Cria a tabela se ela não existir
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
                    chat_id INTEGER PRIMARY KEY,
                    message TEXT)''')
    conn.commit()
    conn.close()

# Função para buscar o histórico de mensagens do banco de dados
def get_memory(chat_id):
    conn = sqlite3.connect('memory.db')
    c = conn.cursor()
    c.execute('SELECT message FROM conversations WHERE chat_id = ?', (chat_id,))
    rows = c.fetchall()
    conn.close()
    # Retorna as mensagens armazenadas ou uma lista vazia
    return [row[0] for row in rows] if rows else []

# Função para salvar uma nova mensagem no banco de dados
def save_message(chat_id, message):
    conn = sqlite3.connect('memory.db')
    c = conn.cursor()
    # Verifica se já existe um histórico para o chat_id
    c.execute('SELECT message FROM conversations WHERE chat_id = ?', (chat_id,))
    if c.fetchone():
        c.execute('UPDATE conversations SET message = message || ? WHERE chat_id = ?', (message, chat_id))
    else:
        c.execute('INSERT INTO conversations (chat_id, message) VALUES (?, ?)', (chat_id, message))
    conn.commit()
    conn.close()

# Inicializa o banco de dados
init_db()

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    print("📥 Mensagem recebida:", data)

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_msg = data["message"]["text"]

        # Recupera o histórico de mensagens
        memory = get_memory(chat_id)

        # Adiciona a nova mensagem à memória
        memory.append(f"User: {user_msg}")

        try:
            # Chama a API da OpenAI com o histórico de mensagens
            chat_completion = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é o Zé do Café, um especialista simpático em café e agricultura."}
                ] + [{"role": "user", "content": msg} for msg in memory]
            )

            # Obtém a resposta da IA
            reply = chat_completion.choices[0].message.content
            print("🤖 Resposta do Zé:", reply)

            # Salva a resposta do bot no banco de dados
            save_message(chat_id, f"Assistant: {reply}")

            # Envia a resposta ao usuário
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


