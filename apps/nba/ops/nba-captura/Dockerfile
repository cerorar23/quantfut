# Imagen del colector NBA (Sprint 1c). Contexto de construcción: apps/nba
#   docker build -f ops/nba-captura/Dockerfile -t nba-captura:<etiqueta> .
FROM python:3.12-slim
RUN pip install --no-cache-dir "psycopg[binary]==3.2.3" "httpx==0.28.1" "tzdata==2026.3"
COPY src/nba /app/src/nba
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
USER 1001:1001
ENTRYPOINT ["python", "-m", "nba.v2.captura"]
