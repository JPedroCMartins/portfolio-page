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
# É ALTAMENTE RECOMENDÁVEL usar variáveis de ambiente em vez de colar os valores aqui.
# No terminal, antes de rodar o app, faça (Linux/macOS):
# export TELEGRAM_BOT_TOKEN="SEU_TOKEN_AQUI"
# export TELEGRAM_CHAT_ID="SEU_CHAT_ID_AQUI"
#
# No Windows (CMD):
# set TELEGRAM_BOT_TOKEN="SEU_TOKEN_AQUI"
# set TELEGRAM_CHAT_ID="SEU_CHAT_ID_AQUI"
#
# (No PowerShell):
# $env:TELEGRAM_BOT_TOKEN="SEU_TOKEN_AQUI"
# $env:TELEGRAM_CHAT_ID="SEU_CHAT_ID_AQUI"

TELEGRAM_BOT_TOKEN = '8554899678:AAFrQZRcF2a9LP6tqVnj8K_r-zU2fc1ntoo'
TELEGRAM_CHAT_ID = 5557053215

# Função para escapar caracteres especiais do MarkdownV2 do Telegram
def escape_markdown(text):
    """Escapa caracteres especiais para o modo MarkdownV2 do Telegram."""
    if not text:
        return ""
    # Lista de caracteres que precisam ser escapados
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    # Adiciona uma barra invertida antes de cada um desses caracteres
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def send_telegram_notification(visitor_info):
    """
    Envia uma mensagem formatada para o chat do Telegram.
    Esta função é executada em uma thread separada.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("!! Variáveis de ambiente TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não definidas.")
        print("!! Notificação não será enviada.")
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
    
    # Dados a serem enviados
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'MarkdownV2' # Habilita a formatação Markdown
    }

    try:
        # Envia a requisição
        requests.post(url, json=payload, timeout=5) # timeout de 5s
        print(f"Notificação do Telegram enviada com sucesso para {ip}")
    except requests.exceptions.RequestException as e:
        # Se falhar, apenas registra no log do servidor, sem quebrar a aplicação
        print(f"Erro ao enviar notificação do Telegram: {e}")

@app.route('/status')
def get_server_status():
    """
    Este é o endpoint de "health check" (verificação de saúde).
    Ele simplesmente retorna um JSON indicando que o servidor está online.
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
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("-" * 50)
        print("AVISO: Variáveis de ambiente TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não foram definidas.")
        print("O servidor irá rodar, mas as notificações do Telegram não funcionarão.")
        print("Configure-as e reinicie o servidor.")
        print("-" * 50)
        
    app.run(host="0.0.0.0", port=8000)