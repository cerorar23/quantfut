# Tennis research engine (non-profit study), isolated from the football services on the same host.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app TENNIS_MOTOR_CONFIG=/data/motor_config.json
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
# Reader of the shared PropLine archive (src/qf/ingest/propline_shared.py of the repository, standard library only),
# copied into the build context beside this Dockerfile; the build fails without it.
COPY propline_shared.py /app/propline_shared.py
WORKDIR /data
