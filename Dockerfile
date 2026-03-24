# ── Stage 1: base ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=38088 \
    MCP_TRANSPORT=http \
    MCP_PATH=/mcp

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip setuptools wheel hatchling && \
    pip install --no-cache-dir ".[test]"

# ── Stage 2: production ───────────────────────────────────────────────────
# API key/secret are injected at runtime via env_file (secrets/pionex.env).
# Never bake credentials into the image.
FROM base AS production

EXPOSE 38088

CMD ["pionex-mcp"]
