from flask import Flask, redirect, url_for, send_from_directory, jsonify
import json
import os

app = Flask(__name__, static_folder="static")

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
