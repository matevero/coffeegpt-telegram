from flask import Flask, request
import requests
import os
import psycopg2
from dotenv import load_dotenv
import google.generativeai as genai

# Carrega variáveis de ambiente
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Nova variável de ambiente para a chave do Gemini
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Configure o Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')

app = Flask(__name__)

# Conecta ao banco de dados
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# Cria tabela se não existir
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    name TEXT,
                    city TEXT
                );
            """)
            conn.commit()

init_db()

# Salva ou atualiza o nome do usuário
def save_user_info(user_id, name=None, city=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE user_id = %s;", (user_id,))
            if cur.fetchone():
                if name:
                    cur.execute("UPDATE users SET name = %s WHERE user_id = %s;", (name, user_id))
                if city:
                    cur.execute("UPDATE users SET city = %s WHERE user_id = %s;", (city, user_id))
            else:
                cur.execute("INSERT INTO users (user_id, name, city) VALUES (%s, %s, %s);", (user_id, name, city))
            conn.commit()

# Busca informações do usuário
def get_user_info(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, city FROM users WHERE user_id = %s;", (user_id,))
            result = cur.fetchone()
            return result if result else (None, None)

# Busca previsão do tempo
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&lang=pt_br&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        desc = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        return f"O clima em {city} agora é {desc}, com temperatura de {temp}°C."
    else:
        return "Não consegui pegar a previsão do tempo. Tem certeza que a cidade está certa?"

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    print("📥 Mensagem recebida:", data)

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_msg = data["message"].get("text", "")
        user_name = data["message"]["from"].get("first_name", "amigo")

        name, city = get_user_info(chat_id)  # Busca as informações do usuário a cada mensagem

        if "meu nome é" in user_msg.lower():
            nome_parts = user_msg.split("meu nome é")[-1].strip().split()
            if nome_parts:
                nome = " ".join(nome_parts)
                save_user_info(chat_id, name=nome)
                send_message(chat_id, f"Beleza, {nome}! Vou lembrar de você.")
            return "ok", 200

        if "minha cidade é" in user_msg.lower():
            cidade_parts = user_msg.split("minha cidade é")[-1].strip().split()
            if cidade_parts:
                cidade = " ".join(cidade_parts)
                save_user_info(chat_id, city=cidade)
                send_message(chat_id, f"Anotado, {cidade}! Vou usar isso pra previsão do tempo.")
            return "ok", 200

        if "previsão do tempo" in user_msg.lower() or "vai chover essa semana" in user_msg.lower():
            if city:
                forecast = get_weather(city)
                send_message(chat_id, forecast)
            else:
                send_message(chat_id, "Você pode me dizer sua cidade? Ex: minha cidade é Machado.")
            return "ok", 200

        prompt = f"Você é o Zé do Café, um especialista simpático em café e agricultura. "
        if name:
            prompt += f"Você está conversando com {name}. "
        if city:
            prompt += f"{name} é da cidade de {city}. "
        prompt += f"Mensagem do usuário: {user_msg}"

        try:
            response = model.generate_content(
                [{"role": "user", "parts": [prompt]}]
            )
            reply = response.text.strip()
            print("🤖 Resposta do Zé:", reply)
            send_message(chat_id, reply)

        except Exception as e:
            print("❌ Erro:", e)
            send_message(chat_id, "Eita, deu ruim aqui com a cabeça do Zé... tenta de novo depois 😅")

    return "ok", 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

