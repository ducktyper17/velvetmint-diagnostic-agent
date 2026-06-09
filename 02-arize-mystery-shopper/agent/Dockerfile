# Self-Improving QA Agent — backend image.
#
# Two-stage build:
#   1. Pull uv to resolve + install Python dependencies from pyproject.toml /
#      uv.lock into a virtualenv-equivalent layout under /opt/venv.
#   2. Final image is python:3.12-slim with Node.js 20 added (we need `npx`
#      at request time so ADK's McpToolset can spawn @arizeai/phoenix-mcp
#      over stdio). We pre-warm the Phoenix MCP package at build time so the
#      first request after cold start doesn't pay the `npx` download cost.

FROM python:3.12-slim AS deps

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv. https://docs.astral.sh/uv/
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml README.md ./
# uv.lock is optional in the scaffold; copy if it exists
COPY uv.loc[k] ./

RUN uv venv /opt/venv \
    && VIRTUAL_ENV=/opt/venv uv pip install --no-cache .


FROM python:3.12-slim AS runtime

# Install Node.js 20 so `npx @arizeai/phoenix-mcp@latest` works.
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
       | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
       > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Pre-warm the Phoenix MCP package so cold-start doesn't hit npm registry.
ENV NPM_CONFIG_CACHE=/opt/npm-cache
RUN mkdir -p /opt/npm-cache \
    && npm install --prefix /opt/phoenix-mcp @arizeai/phoenix-mcp@latest \
    && ln -s /opt/phoenix-mcp/node_modules/.bin/phoenix-mcp /usr/local/bin/phoenix-mcp || true

# Bring over the dependency layer.
COPY --from=deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY qa_agent ./qa_agent
COPY sut ./sut
COPY scenarios.py judge_prompts.py ./
# Canonical "winning" delta report shipped with the image so the live demo's
# "Show loop report" button has data without needing a fresh audit run.
COPY delta_report.json ./

ENV PORT=8080 \
    APP_ENV=production \
    PHOENIX_MCP_COMMAND=npx \
    PHOENIX_MCP_ARGS=-y,@arizeai/phoenix-mcp@latest

EXPOSE 8080
CMD ["uvicorn", "qa_agent.main:app", "--host", "0.0.0.0", "--port", "8080"]
