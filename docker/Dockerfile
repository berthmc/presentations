FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    NODE_VERSION=20

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-impress \
    libreoffice-draw \
    poppler-utils \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@11.17.0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY scripts ./scripts
COPY backend/presentations/compile/node/package.json ./backend/presentations/compile/node/package.json
COPY backend/presentations/compile/node/builder.mjs ./backend/presentations/compile/node/builder.mjs

RUN pip install --upgrade pip \
    && pip install ".[dev]" \
    && cd backend/presentations/compile/node && npm install --omit=dev

RUN mkdir -p /data/staging /data/output /data/templates /data/uploads /data/qa

EXPOSE 8090 8091

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
