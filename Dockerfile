# Pinned base image (was: python:3.11-slim)
FROM python@sha256:e4676722fba839e2e5cdb844a52262b43e90e56dbd55b7ad953ee3615ad7534f

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY bot.py storage.py webhook.py config.json entrypoint.py ./

# Create data directory
RUN mkdir -p data

# Expose port (default 8000, but Max supports 80, 8080, 443, 8443, 16384-32383)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run entrypoint: bot + webhook (can be configured with BOT_MODE env var)
# BOT_MODE=bot -> only long-polling bot
# BOT_MODE=webhook -> only WebHook server
# BOT_MODE=both (default) -> both bot + webhook
CMD ["python", "entrypoint.py", "both"]
