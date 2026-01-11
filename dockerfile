FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache
COPY . .

EXPOSE 8000

CMD ["uv", "run", "gunicorn", "--workers", "3", "--bind", "0.0.0.0:8000", "app:app"]