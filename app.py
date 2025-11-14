from flask import Flask, redirect, url_for, send_from_directory, jsonify, request
from flask_cors import CORS
import json
import os
import requests  # Importa a biblioteca de requisições HTTP
import threading # Para enviar mensagens em segundo plano
from datetime import datetime
import re       # Para "escapar" caracteres especiais do Markdown

app = Flask(__name__, static_folder="static")
CORS(app)

# --- Configuração do Bot do Telegram ---
# O TOKEN ainda é necessário para o bot ENVIAR mensagens.
# No terminal, antes de rodar o app, faça (Linux/macOS):
# export TELEGRAM_BOT_TOKEN="SEU_TOKEN_AQUI"
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Este arquivo irá armazenar os chat_ids dos usuários inscritos.
# O outro script (bot_listener.py) irá preenchê-lo.
SUBSCRIBERS_FILE = 'subscribers.json'

# Função para escapar caracteres especiais do MarkdownV2 do Telegram
def escape_markdown(text):
    """Escapa caracteres especiais para o modo MarkdownV2 do Telegram."""
    if not text:
        return ""
    # Lista de caracteres que precisam ser escapados
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    # Adiciona uma barra invertida antes de cada um desses caracteres
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def get_subscribers():
    """Lê a lista de IDs de assinantes do arquivo JSON."""
    if not os.path.exists(SUBSCRIBERS_FILE):
        return [] # Retorna lista vazia se o arquivo não existir
    
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            data = json.load(f)
            # Espera-se que o JSON contenha uma lista de IDs
            if isinstance(data, list):
                return data
            else:
                return []
    except json.JSONDecodeError:
        print(f"Erro ao ler o arquivo {SUBSCRIBERS_FILE}. Arquivo corrompido?")
        return []
    except Exception as e:
        print(f"Erro inesperado ao ler {SUBSCRIBERS_FILE}: {e}")
        return []

def send_telegram_notification(visitor_info):
    """
    Envia uma mensagem formatada para TODOS os assinantes.
    Esta função é executada em uma thread separada.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("!! Variável de ambiente TELEGRAM_BOT_TOKEN não definida.")
        print("!! Notificação não será enviada.")
        return

    subscribers = get_subscribers()
    if not subscribers:
        print("Nenhum assinante encontrado. Nenhuma notificação será enviada.")
        return

    # Formata a data e hora
    now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    # Coleta e escapa as informações para o Markdown
    ip = escape_markdown(visitor_info.get('ip', 'N/A'))
    user_agent = escape_markdown(visitor_info.get('user_agent', 'N/A'))
    referrer = escape_markdown(visitor_info.get('referrer', 'N/A'))
    
    # Monta a mensagem usando MarkdownV2 do Telegram
    message = (
        f"🔔 *Novo Acesso ao Site* \n\n"
        f"📅 *Horário:* `{now}`\n"
        f"👤 *IP:* `{ip}`\n"
        f"🌐 *Referer:* `{referrer}`\n\n"
        f"💻 *User Agent (Navegador/SO):*\n"
        f"```{user_agent}```"
    )
    
    # URL da API do Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Envia a notificação para CADA assinante
    print(f"Enviando notificação para {len(subscribers)} assinante(s)...")
    for chat_id in subscribers:
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'MarkdownV2' # Habilita a formatação Markdown
        }

        try:
            # Envia a requisição
            requests.post(url, json=payload, timeout=5) # timeout de 5s
        except requests.exceptions.RequestException as e:
            # Se falhar para um usuário, apenas registra e continua para o próximo
            print(f"Erro ao enviar notificação para {chat_id}: {e}")
    
    print(f"Notificações enviadas com sucesso para {ip}")

@app.route('/status')
def get_server_status():
    """
    Este é o endpoint de "health check" (verificação de saúde).
    """
    try:
        response = {
            "status": "online",
            "message": "Servidor operando normalmente."
        }
        return jsonify(response), 200 # Retorna o JSON e o código de status 200 (OK)
    
    except Exception as e:
        response = {
            "status": "error",
            "message": str(e)
        }
        return jsonify(response), 500 # Retorna erro 500 (Internal Server Error)

@app.route('/')
def serve_index():
    """
    Serve a página principal e dispara a notificação do Telegram.
    """
    try:
        # --- Início da Notificação ---
        # Coleta as informações do visitante
        visitor_info = {
            # Tenta obter o IP real, mesmo se estiver atrás de um proxy (como Heroku/Render)
            "ip": request.headers.get('X-Forwarded-For', request.remote_addr),
            "user_agent": str(request.user_agent),
            "referrer": str(request.referrer) if request.referrer else 'Acesso Direto'
        }
        
        # Cria e inicia uma thread para enviar a notificação em segundo plano
        # Isso evita que o usuário tenha que esperar a notificação ser enviada
        notification_thread = threading.Thread(
            target=send_telegram_notification,
            args=(visitor_info,)
        )
        notification_thread.start()
        # --- Fim da Notificação ---

    except Exception as e:
        print(f"Erro ao tentar iniciar a thread de notificação: {e}")
        # Continua a servir a página mesmo se a coleta de dados falhar
    
    # Envia o arquivo index.html como antes
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/qr_code')
def qr_code():
    # Caminho do arquivo de acesso
    caminho_arquivo = 'acesso.json'

    # Se o arquivo existir, lê o número atual de acessos
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, 'r') as f:
            dados = json.load(f)
            acessos = dados.get('acessos', 0)
    else:
        acessos = 0

    # Soma +1
    acessos += 1

    # Salva o novo valor
    with open(caminho_arquivo, 'w') as f:
        json.dump({'acessos': acessos}, f, indent=2)

    # Redireciona para a função serve_index
    # A função 'serve_index' cuidará de enviar a notificação do Telegram
    return redirect(url_for('serve_index'))

@app.route('/qrcode/ver_acessos')
def ver_acessos():
    caminho_arquivo = 'acesso.json'
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, 'r') as f:
            dados = json.load(f)
    else:
        dados = {'acessos': 0}
    return jsonify(dados)

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        print("-" * 50)
        print("AVISO: Variável de ambiente TELEGRAM_BOT_TOKEN não definida.")
        print("O servidor irá rodar, mas as notificações do Telegram não funcionarão.")
        print("Configure-a e reinicie o servidor.")
        print("-" * 50)
        
    app.run(host="0.0.0.0", port=8000)