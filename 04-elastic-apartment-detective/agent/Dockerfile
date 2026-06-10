# Apartment Detective — backend image.
FROM python:3.12-slim AS deps
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml ./
COPY uv.loc[k] ./
RUN uv venv /opt/venv \
    && VIRTUAL_ENV=/opt/venv uv pip install --no-cache .

FROM python:3.12-slim AS runtime
COPY --from=deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY src ./src
ENV PORT=8080 ENVIRONMENT=prod
EXPOSE 8080
CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "src"]
