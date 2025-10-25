# Usa uma imagem Python leve
FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /app

# Copia o código e os arquivos da landing
COPY . .

# Instala Flask e Gunicorn (servidor de produção)
RUN pip install --no-cache-dir flask gunicorn

# Expõe a porta 8000
EXPOSE 8000

# Usa Gunicorn em vez do servidor de desenvolvimento
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
