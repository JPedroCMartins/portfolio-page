from flask import Flask, redirect, url_for, send_from_directory, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__, static_folder="static")
CORS(app)
@app.route('/status')
def get_server_status():
    """
    Este é o endpoint de "health check" (verificação de saúde).
    Ele simplesmente retorna um JSON indicando que o servidor está online.
    """
    try:
        # No futuro, você poderia adicionar lógicas mais complexas aqui,
        # como verificar a conexão com o banco de dados.
        
        response = {
            "status": "online",
            "message": "Servidor operando normalmente."
        }
        return jsonify(response), 200 # Retorna o JSON e o código de status 200 (OK)
    
    except Exception as e:
        # Se algo der errado na sua verificação
        response = {
            "status": "error",
            "message": str(e)
        }
        return jsonify(response), 500 # Retorna erro 500 (Internal Server Error)

@app.route('/')
def serve_index():
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
    app.run(host="0.0.0.0", port=8000)
