# syntax=docker/dockerfile:1

## ---- Stage 1: build dependencies ----
FROM python:3.10-slim AS builder

WORKDIR /build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

## ---- Stage 2: runtime image ----
FROM python:3.10-slim AS runtime

# Non-critical defaults configured directly in the image; SECRET_KEY and
# DATABASE_URL are intentionally NOT defaulted here - they must be injected
# at runtime (see docker-compose.yaml / .env).
ENV BACKEND_PORT=5000 \
    GUNICORN_WORKERS=3 \
    DEBUG=false \
    ALLOWED_HOSTS=* \
    CORS_ORIGINS=* \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

RUN groupadd --system conduit && useradd --system --gid conduit --create-home conduit

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=conduit:conduit . .
RUN chmod +x entrypoint.sh

USER conduit

EXPOSE ${BACKEND_PORT}

ENTRYPOINT ["./entrypoint.sh"]
