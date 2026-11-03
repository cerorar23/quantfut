# Imagen de la API de lectura NBA v2 (Sprint 6). Contexto de construcción: apps/nba
#   docker build -f ops/nba-api/Dockerfile -t nba-api:<etiqueta> .
FROM python:3.12-slim
RUN pip install --no-cache-dir "psycopg[binary]==3.2.3" "numpy==2.1.3" "fastapi==0.115.6" "uvicorn==0.34.0"
COPY src/nba /app/src/nba
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
USER 1001:1001
# NBA_DB_DSN_LECTOR: usuario de solo lectura de nba_datos (se crea al desplegar; la API además abre cada conexión en modo solo lectura)
ENTRYPOINT ["python", "-m", "uvicorn", "nba.api.app:app_desde_entorno", "--factory", "--host", "0.0.0.0", "--port", "8000"]
