from flask import Flask, redirect, url_for, send_from_directory, jsonify, request
from flask_cors import CORS
import json
import os
import threading 
from datetime import datetime
import re
import asyncio  # <-- 1. IMPORTADO O ASYNCIO

# --- Imports do Telegram ---
import telegram
from telegram.constants import ParseMode
from telegram.error import TelegramError

app = Flask(__name__, static_folder="static")
CORS(app)

# --- Configuração do Bot do Telegram ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
SUBSCRIBERS_FILE = 'subscribers.json'

# --- Inicializa o objeto do Bot ---
bot = None
if TELEGRAM_BOT_TOKEN:
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
else:
    print("!! Variável de ambiente TELEGRAM_BOT_TOKEN não definida.")
    print("!! Notificações do Telegram não funcionarão.")
# --------------------------------------

def escape_markdown(text):
    """Escapa caracteres especiais para o modo MarkdownV2 do Telegram."""
    if not text:
        return ""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def get_subscribers():
    """Lê a lista de IDs de assinantes do arquivo JSON."""
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        print(f"Erro ao ler o arquivo {SUBSCRIBERS_FILE}. Arquivo corrompido?")
        return []
    except Exception as e:
        print(f"Erro inesperado ao ler {SUBSCRIBERS_FILE}: {e}")
        return []

# --- 2. NOVA FUNÇÃO HELPER ASSÍNCRONA ---
async def _send_all_messages_async(subscribers, message_text):
    """
    Função assíncrona que de fato envia as mensagens, uma por uma.
    """
    if not bot:
        print("!! Bot não inicializado na função async.")
        return

    parse_mode = ParseMode.MARKDOWN_V2

    for chat_id in subscribers:
        try:
            # Aqui usamos 'await' pois estamos em uma função 'async def'
            await bot.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode=parse_mode
            )
        except TelegramError as e:
            # A biblioteca fornece tipos de erro específicos
            # CORREÇÃO: Usamos 'e' diretamente, em vez de 'e.description'
            print(f"Erro Telegram ao enviar para {chat_id}: {e}")
        except Exception as e:
            print(f"Erro inesperado ao enviar para {chat_id}: {e}")

# --- 3. FUNÇÃO ORIGINAL (SÍNCRONA) MODIFICADA ---
def send_telegram_notification(visitor_info):
    """
    Prepara a mensagem e dispara a execução assíncrona.
    Esta função (síncrona) é o que a Thread irá executar.
    """
    if not bot:
        print("!! Objeto do Bot não inicializado. Notificação cancelada.")
        return

    subscribers = get_subscribers()
    if not subscribers:
        print("Nenhum assinante encontrado. Nenhuma notificação será enviada.")
        return

    now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    # CORREÇÃO: Não escapar NADA que vá dentro de blocos de código (`...` ou ```...```)
    ip = visitor_info.get('ip', 'N/A')
    user_agent = visitor_info.get('user_agent', 'N/A')
    referrer = visitor_info.get('referrer', 'N/A')
    
    # CORREÇÃO: O bloco de código ``` deve estar em linhas separadas
    message = (
        f"🔔 *Novo Acesso ao Site* \n\n"
        f"📅 *Horário:* `{now}`\n"
        f"👤 *IP:* `{ip}`\n"
        f"🌐 *Referer:* `{referrer}`\n\n"
        f"💻 *User Agent:*\n"
        f"```\n"  # <-- Linha 1 do bloco
        f"{user_agent}\n"  # <-- Conteúdo
        f"```"  # <-- Linha 3 do bloco
    )
    
    print(f"Enviando notificação para {len(subscribers)} assinante(s)...")
    
    try:
        # Ponto principal da mudança:
        # asyncio.run() cria um novo loop de eventos, executa a
        # coroutine _send_all_messages_async e fecha o loop.
        asyncio.run(_send_all_messages_async(subscribers, message))
        
        print(f"Notificações enviadas com sucesso para {ip}")
        
    except Exception as e:
        print(f"Erro ao executar asyncio.run(): {e}")

# --- O restante do seu código Flask permanece igual ---

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
        return jsonify(response), 200
    except Exception as e:
        response = {
            "status": "error",
            "message": str(e)
        }
        return jsonify(response), 500

@app.route('/')
def serve_index():
    """
    Serve a página principal e dispara a notificação do Telegram.
    """
    try:
        visitor_info = {
            "ip": request.headers.get('X-Forwarded-For', request.remote_addr),
            "user_agent": str(request.user_agent),
            "referrer": str(request.referrer) if request.referrer else 'Acesso Direto'
        }
        
        # A thread continua igual, chamando a função síncrona
        notification_thread = threading.Thread(
            target=send_telegram_notification,
            args=(visitor_info,)
        )
        notification_thread.start()

    except Exception as e:
        print(f"Erro ao tentar iniciar a thread de notificação: {e}")
    
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/qr_code')
def qr_code():
    caminho_arquivo = 'acesso.json'
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, 'r') as f:
            dados = json.load(f)
            acessos = dados.get('acessos', 0)
    else:
        acessos = 0
    acessos += 1
    with open(caminho_arquivo, 'w') as f:
        json.dump({'acessos': acessos}, f, indent=2)
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
    if not bot: # Verifica se o bot foi inicializado
        print("-" * 50)
        print("AVISO: O objeto do Bot não foi inicializado (Token ausente).")
        print("O servidor irá rodar, mas as notificações do Telegram não funcionarão.")
        print("-" * 50)
        
    app.run(host="0.0.0.0", port=8000)