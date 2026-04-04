import json
import os
from flask import Flask, redirect, render_template, url_for, send_from_directory, jsonify
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

ACESSO_FILE = 'acesso.json'

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

def _ler_acessos():
    """
    Função auxiliar para ler a quantidade de acessos do arquivo de forma segura.
    """
    if os.path.exists(ACESSO_FILE):
        with open(ACESSO_FILE, 'r') as f:
            try:
                dados = json.load(f)
                return dados.get('acessos', 0)
            except json.JSONDecodeError:
                pass
    return 0

@app.route('/qr_code')
def qr_code():
    """
    Incrementa o contador de acessos e redireciona para a home.
    """
    acessos = _ler_acessos() + 1
    
    # Salva a nova contagem
    with open(ACESSO_FILE, 'w') as f:
        json.dump({'acessos': acessos}, f, indent=2)
        
    return redirect(url_for('serve_index'))

@app.route('/qrcode/ver_acessos')
def ver_acessos():
    """
    Retorna o JSON com a contagem de acessos.
    """
    return jsonify({'acessos': _ler_acessos()})

@app.route('/<path:path>')
def serve_static(path):
    """
    Serve arquivos estáticos genéricos.
    """
    return send_from_directory(app.static_folder, path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
