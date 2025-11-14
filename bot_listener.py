import requests
import os
import time
import json

# --- Configuração ---
# Pega o token da variável de ambiente
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
# Pega a senha que o bot vai exigir
BOT_PASSWORD = os.environ.get('BOT_PASSWORD')

# Arquivo para salvar os IDs dos assinantes
SUBSCRIBERS_FILE = 'subscribers.json'

# Dicionário em memória para rastrear o estado da conversa de cada usuário
# Ex: {12345: "awaiting_password"}
user_states = {}

# --- Funções de Ajuda ---

def get_me(token):
    """Verifica se o token é válido e mostra o nome do bot."""
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get('ok'):
            bot_username = data['result']['username']
            print("-" * 30)
            print(f"Conectado com sucesso ao bot: @{bot_username}")
            print("Ouvindo por comandos... (Pressione Ctrl+C para parar)")
            print("-" * 30)
            return True
        else:
            print(f"Erro ao conectar: {data.get('description')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Erro de rede ou token inválido: {e}")
        return False

def send_message(chat_id, text):
    """Envia uma mensagem de texto para um chat_id específico."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    try:
        requests.post(url, json=payload, timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem para {chat_id}: {e}")

def get_subscribers():
    """Lê a lista de IDs de assinantes do arquivo JSON."""
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []

def save_subscribers(subscribers):
    """Salva a lista atualizada de assinantes no arquivo JSON."""
    with open(SUBSCRIBERS_FILE, 'w') as f:
        json.dump(subscribers, f, indent=2)

def handle_update(update):
    """Processa uma única mensagem/update do Telegram."""
    global user_states
    
    if 'message' not in update:
        return # Ignora updates que não são mensagens (ex: edições)

    message = update['message']
    chat_id = message['chat']['id']
    text = message.get('text', '').strip()

    if not text:
        return # Ignora mensagens sem texto (ex: fotos, stickers)

    # --- Lógica de Comandos ---

    subscribers = get_subscribers()

    if text == '/start':
        if chat_id in subscribers:
            send_message(chat_id, "Você já está inscrito e recebendo notificações. Para parar, envie /stop.")
        else:
            send_message(chat_id, "Olá! Este é um bot privado. Por favor, digite a senha para começar a receber notificações de acesso ao site.")
            user_states[chat_id] = "awaiting_password" # Marca que estamos esperando a senha deste usuário

    elif text == '/stop':
        if chat_id in subscribers:
            subscribers.remove(chat_id)
            save_subscribers(subscribers)
            send_message(chat_id, "Você não receberá mais notificações. Para reativar, envie /start.")
        else:
            send_message(chat_id, "Você não estava inscrito.")
        user_states.pop(chat_id, None) # Limpa o estado

    elif user_states.get(chat_id) == "awaiting_password":
        if text == BOT_PASSWORD:
            if chat_id not in subscribers:
                subscribers.append(chat_id)
                save_subscribers(subscribers)
            send_message(chat_id, "✅ Sucesso! Senha correta. Você agora está inscrito e receberá notificações de acesso.")
            user_states.pop(chat_id, None) # Limpa o estado
        else:
            send_message(chat_id, "❌ Senha incorreta. Tente novamente ou envie /stop para cancelar.")

    # Ignora outras mensagens que não são comandos ou senhas
    elif text.startswith('/'):
        send_message(chat_id, "Comando desconhecido. Use /start para se inscrever ou /stop para cancelar.")

def listen_for_updates():
    """Função principal que fica em loop ouvindo o Telegram."""
    offset = 0
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

    while True:
        try:
            params = {'timeout': 100, 'offset': offset, 'limit': 10}
            response = requests.get(url, params=params, timeout=105)
            data = response.json()
            
            if data['ok'] and data['result']:
                for update in data['result']:
                    handle_update(update)
                    offset = update['update_id'] + 1 # Atualiza o offset para a próxima mensagem
            
        except requests.exceptions.ReadTimeout:
            continue # Normal para long polling
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}. Tentando novamente em 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nDesligando o listener...")
            break

if __name__ == "__main__":
    if not TOKEN:
        print("Erro: Variável de ambiente TELEGRAM_BOT_TOKEN não definida.")
    elif not BOT_PASSWORD:
        print("Erro: Variável de ambiente TELEGRAM_BOT_PASSWORD não definida.")
        print("Por favor, defina a senha que os usuários deverão digitar.")
    elif get_me(TOKEN):
        listen_for_updates()