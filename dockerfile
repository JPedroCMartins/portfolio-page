# Usa uma imagem Python leve
FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /app

# 1. Copia APENAS o arquivo de dependências
COPY requirements.txt .

# 2. Instala as dependências
# Isso fica em cache e não roda toda vez
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copia TODO o resto do código
COPY . .

# Expõe a porta 8000 (para o Gunicorn)
EXPOSE 8000

# O comando CMD será definido no docker-compose
# Deixamos um aqui como padrão, mas o compose irá sobrescrevê-lo.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]