from flask import Flask, request
import requests
from openai import OpenAI
import os
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# Função para pegar a previsão do tempo
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHERMAP_API_KEY}&lang=pt_br&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        clima = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        sensacao = data["main"]["feels_like"]
        return f"Em {city}, o clima agora é '{clima}' com temperatura de {temp}°C (sensação térmica de {sensacao}°C)."
    else:
        return "Não consegui encontrar o clima dessa cidade 😓"

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    print("📥 Mensagem recebida:", data)

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_msg = data["message"]["text"]

        if "clima" in user_msg.lower() or "tempo" in user_msg.lower():
            palavras = user_msg.split()
            cidade = None
            for i, palavra in enumerate(palavras):
                if palavra.lower() in ["em", "de"] and i + 1 < len(palavras):
                    cidade = palavras[i + 1]
                    break

            if cidade:
                previsao = get_weather(cidade)
                send_message(chat_id, previsao)
            else:
                send_message(chat_id, "Me diga o nome da cidade para eu ver o clima! Ex: 'Como está o clima em Campinas?'")
            return "ok", 200

        try:
            chat_completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é o Zé do Café, um especialista simpático em café e agricultura."},
                    {"role": "user", "content": user_msg}
                ]
            )

            reply = chat_completion.choices[0].message.content
            print("🤖 Resposta do Zé:", reply)
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




