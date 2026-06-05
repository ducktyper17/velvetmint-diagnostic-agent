FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    SYNTHETIC_DATA_ROOT=/synthetic-data

WORKDIR /app

COPY 01-fivetran-dtc-diagnostic/mock-saas/pyproject.toml ./pyproject.toml
COPY 01-fivetran-dtc-diagnostic/mock-saas/README.md ./README.md
COPY 01-fivetran-dtc-diagnostic/mock-saas/src ./src
COPY synthetic-data /synthetic-data

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

CMD ["python", "-m", "uvicorn", "mock_saas.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8080"]
