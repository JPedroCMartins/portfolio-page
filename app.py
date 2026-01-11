from flask import Flask, redirect, render_template, url_for, send_from_directory, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__, static_folder="static")
CORS(app)

@app.route('/status')
def get_server_status():
    """
    Endpoint de "health check" (verificação de saúde).
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
    Serve a página principal.
    """
    return render_template("index.html")

@app.route('/qr_code')
def qr_code():
    """
    Incrementa o contador de acessos e redireciona para a home.
    """
    caminho_arquivo = 'acesso.json'
    
    # Lê o contador atual
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, 'r') as f:
            try:
                dados = json.load(f)
                acessos = dados.get('acessos', 0)
            except json.JSONDecodeError:
                acessos = 0
    else:
        acessos = 0
    
    # Incrementa e salva
    acessos += 1
    with open(caminho_arquivo, 'w') as f:
        json.dump({'acessos': acessos}, f, indent=2)
        
    return redirect(url_for('serve_index'))

@app.route('/qrcode/ver_acessos')
def ver_acessos():
    """
    Retorna o JSON com a contagem de acessos.
    """
    caminho_arquivo = 'acesso.json'
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, 'r') as f:
            try:
                dados = json.load(f)
            except json.JSONDecodeError:
                dados = {'acessos': 0}
    else:
        dados = {'acessos': 0}
    return jsonify(dados)

@app.route('/<path:path>')
def serve_static(path):
    """
    Serve arquivos estáticos genéricos.
    """
    return send_from_directory(app.static_folder, path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)