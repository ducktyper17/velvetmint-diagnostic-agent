# Doctor's Note Decoder — single Cloud Run service.
#
# The image bundles BOTH Python (the agent) and Node (the official MongoDB
# MCP server, launched over stdio by main.lifespan via `npx`). Keeping them
# in one container means one Cloud Run service, no cross-service networking,
# and no CORS surface for the demo UI.

FROM python:3.11-slim

# --- Node.js 20 (for the MongoDB MCP server) -------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pin the MCP server version into the image so a demo never pulls a
# surprise release at request time. Override MCP_SERVER_ARGS to re-point.
ARG MONGODB_MCP_VERSION=latest
RUN npm install -g "mongodb-mcp-server@${MONGODB_MCP_VERSION}"
ENV MCP_SERVER_CMD=mongodb-mcp-server \
    MCP_SERVER_ARGS="--connection-string ${MONGODB_URI}"

WORKDIR /app

# Install Python deps first for layer caching.
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# App code + the single-page UI.
COPY *.py ./
COPY static ./static

# Cloud Run injects PORT; default to 8080 for local `docker run`.
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
