.PHONY: setup backend-dev frontend-dev test lint elastic-setup ingest seed deploy deploy-backend deploy-frontend

PY ?= ./agent/.venv/bin/python

# --- setup ---

setup:
	cd agent    && python3.11 -m venv .venv && ./.venv/bin/pip install -e ".[dev,ingest]"
	cd frontend && npm install

# --- local dev (run each in its own terminal) ---

backend-dev:
	cd agent    && ./.venv/bin/uvicorn agent.main:app --reload --port 8080 --app-dir src

frontend-dev:
	cd frontend && BACKEND_URL=http://localhost:8080 npm run dev

# --- quality ---

test:
	cd agent && ./.venv/bin/pytest -q

lint:
	cd agent && ./.venv/bin/ruff check src/ && ./.venv/bin/mypy src/

# --- Elastic provisioning (needs ELASTIC_ENDPOINT + ELASTIC_API_KEY) ---

elastic-setup:
	cd agent && ./.venv/bin/python scripts/elastic_setup.py

ingest:
	cd agent && ./.venv/bin/python scripts/ingest_nyc.py --zips 10002,10009

seed:
	cd agent && ./.venv/bin/python scripts/seed_tenant_signals.py

# --- deploy to Cloud Run ---

deploy: deploy-backend deploy-frontend

deploy-backend:
	./scripts/deploy.sh backend

deploy-frontend:
	./scripts/deploy.sh frontend
