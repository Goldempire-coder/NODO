FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/apps/api
ENV WEB_CONCURRENCY=1
ENV UVICORN_ACCESS_LOG=0

WORKDIR /app

COPY apps/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY apps/api ./apps/api
COPY database ./database
COPY scripts ./scripts

EXPOSE 8000

CMD ["sh", "-c", "if [ \"${UVICORN_ACCESS_LOG:-0}\" = \"1\" ]; then ACCESS_LOG=''; else ACCESS_LOG='--no-access-log'; fi; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} $ACCESS_LOG"]
