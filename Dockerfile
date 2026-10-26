FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml ./
COPY opsagent ./opsagent
COPY docs ./docs

RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install -e . && \
    python -m playwright install --with-deps chromium

RUN mkdir -p /app/data

EXPOSE 8000 8001

# Start script runs both sandbox and dashboard
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

CMD ["/app/start.sh"]
