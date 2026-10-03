FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EMAIL_VAULT_ENV=production \
    EMAIL_VAULT_STORAGE_ROOT=/data/email-vault-storage \
    DATABASE_URL=sqlite:////data/email_vault.db

WORKDIR /app

RUN addgroup --system emailvault \
    && adduser --system --ingroup emailvault emailvault

COPY pyproject.toml README.md ./
COPY services ./services

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir ".[api,renderer]" \
    && python -m playwright install --with-deps chromium \
    && mkdir -p /data/email-vault-storage \
    && chown -R emailvault:emailvault /app /data

USER emailvault

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" || exit 1

CMD ["python", "-m", "uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
