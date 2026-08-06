## ---- Stage 1: build dependencies ----
FROM python:3.5-slim AS builder

WORKDIR /build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

## ---- Stage 2: runtime image ----
FROM python:3.5-slim AS runtime

ENV BACKEND_PORT=5000 \
    GUNICORN_WORKERS=3 \
    DEBUG=false \
    ALLOWED_HOSTS=* \
    CORS_ORIGINS=* \
    DB_HOST=database \
    DB_PORT=5432 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

RUN printf 'deb http://archive.debian.org/debian buster main\n\
deb http://archive.debian.org/debian-security buster/updates main\n' \
        > /etc/apt/sources.list \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install --no-install-recommends -y postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system conduit && useradd --system --gid conduit --create-home conduit

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=conduit:conduit . .
RUN chmod +x entrypoint.sh

USER conduit

EXPOSE ${BACKEND_PORT}

ENTRYPOINT ["./entrypoint.sh"]
