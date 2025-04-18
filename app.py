from flask import Flask, request
import requests
import os
import psycopg2
from dotenv import load_dotenv
import google.generativeai as genai
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Nova variável de ambiente para a chave do Gemini
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Configure o Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')  # Mantenha ou ajuste o modelo conforme necessário

app = Flask(__name__)

# Conecta ao banco de dados (mantenha)
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# Cria tabela se não existir (mantenha)
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

# Salva ou atualiza o nome do usuário (mantenha)
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

# Busca informações do usuário (mantenha)
def get_user_info(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, city FROM users WHERE user_id = %s;", (user_id,))
            result = cur.fetchone()
            return result if result else (None, None)

# Busca previsão do tempo (mantenha)
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

def iniciar_driver():
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')  # Executar o Chrome em modo headless (sem interface gráfica) para o Render
    return webdriver.Chrome(service=service, options=options)

def check_internet_connection():
    try:
        requests.get('https://www.google.com', timeout=5)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False

def abrir_site_e_coletar_dados(driver):
    url = 'http://www.agnocafe.com.br/'
    logging.info(f'Acessando {url}')
    for attempt in range(5):
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 20)

            dados = {
                'ny': wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[4]/div[2]/div[2]/table[1]/tbody/tr[3]'))).text,
                'londres': driver.find_element(By.XPATH, '/html/body/div[1]/div[4]/div[2]/div[2]/table[2]/tbody/tr[3]').text,
                'moeda': driver.find_element(By.XPATH, '//*[@id="corpo"]/div[2]/div[2]/table[4]/tbody/tr[4]').text,
                'bmf': driver.find_element(By.XPATH, '/html/body/div[1]/div[4]/div[2]/div[2]/table[3]/tbody/tr[3]').text,
                'outro': driver.find_element(By.XPATH, '//*[@id="corpo"]/div[2]/div[1]/div[1]/div[2]/table/tbody/tr[2]/td/a').text
            }
            return dados
        except (NoSuchElementException, TimeoutException) as e:
            logging.warning(f'Tentativa {attempt + 1} falhou ao coletar dados: {e}. Tentando novamente...')
            time.sleep(5)
    raise Exception("Falha ao carregar dados do site após várias tentativas.")

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

        if "cotação do café" in user_msg.lower():
            driver = iniciar_driver()
            try:
                if check_internet_connection():
                    dados_cotacao = abrir_site_e_coletar_dados(driver)
                    mensagem_cotacao = f"*Cotações do Café (Agnocafe.com.br)*:\n\n"
                    mensagem_cotacao += f"`BOLSA DE NEW YORK:`\n {dados_cotacao['ny']}\n\n"
                    mensagem_cotacao += f"`BOLSA DE LONDRES:`\n {dados_cotacao['londres']}\n\n"
                    mensagem_cotacao += f"`BM&F:`\n {dados_cotacao['bmf']}\n\n"
                    mensagem_cotacao += f"`MOEDA:`\n {dados_cotacao['moeda']}\n\n"
                    mensagem_cotacao += f"`OUTRAS INFORMAÇÕES:`\n {dados_cotacao['outro']}\n"
                    send_message(chat_id, mensagem_cotacao)
                else:
                    send_message(chat_id, "Não foi possível acessar as cotações do café devido à falta de conexão com a internet.")
            except Exception as e:
                logging.error(f"Erro ao obter cotações: {e}")
                send_message(chat_id, "Ocorreu um erro ao buscar as cotações do café.")
            finally:
                driver.quit()
            return "ok", 200

        if "photo" in data["message"]:
            try:
                file_id = data["message"]["photo"][-1]["file_id"]
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
                response = requests.get(url).json()
                file_path = response["result"]["file_path"]
                image_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                image_response = requests.get(image_url)
                image_bytes = image_response.content
                mime_type = image_response.headers["Content-Type"]

                prompt_image = f"O que você pode me dizer sobre esta imagem? {user_msg if user_msg else ''}"
                response_gemini = model.generate_content([
                    {"role": "user", "parts": [
                        {"text": prompt_image},
                        {"image": image_bytes, "mime_type": mime_type}
                    ]}
                ])
                reply = response_gemini.text.strip()
                print("🤖 Resposta da análise da imagem:", reply)
                send_message(chat_id, reply)

            except Exception as e:
                print("❌ Erro ao analisar a imagem:", e)
                send_message(chat_id, "Eita, não consegui analisar essa imagem 😅")
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
