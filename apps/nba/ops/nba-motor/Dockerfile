# Imagen del motor v2 (Sprint 5): lo del colector más numpy y scipy. Contexto de construcción: apps/nba
#   docker build -f ops/nba-motor/Dockerfile -t nba-motor:<etiqueta> .
FROM python:3.12-slim
RUN pip install --no-cache-dir "psycopg[binary]==3.2.3" "httpx==0.28.1" "tzdata==2026.3" "numpy==2.1.3" "scipy==1.14.1" "pydantic==2.14.2"
COPY src/nba /app/src/nba
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
USER 1001:1001
