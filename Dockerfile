FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git cron ca-certificates openssh-client \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/
COPY frontend/ /app/frontend/
# Motor de tenis (la API importa `tenis.*`): solo src y config, como la imagen que corre en producción.
COPY apps/tenis/src/ /app/apps/tenis/src/
COPY apps/tenis/config/ /app/apps/tenis/config/
ENV PYTHONPATH=/app/src:/app/apps/tenis/src
RUN mkdir -p /srv/quantfut/chain /srv/quantfut/artifacts

CMD ["uvicorn", "qf.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
