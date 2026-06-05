.PHONY: setup demo-app-dev backend-dev frontend-dev traffic-healthy traffic-bad deploy deploy-demo-app deploy-backend deploy-frontend

PY ?= uv run python

setup:
	cd agent     && uv sync
	cd demo-app  && uv sync
	cd frontend  && npm install

# --- local dev (run each in its own terminal) ---

demo-app-dev:
	cd demo-app && uv run uvicorn refund_assistant.main:app --reload --port 8090 --app-dir src

backend-dev:
	cd agent    && uv run uvicorn agent.main:app --reload --port 8080 --app-dir src

frontend-dev:
	cd frontend && BACKEND_URL=http://localhost:8080 npm run dev

# --- traffic generation ---

traffic-healthy:
	cd demo-app && $(PY) scripts/traffic.py --mode healthy --requests 25 --release-id release-2026-05-26-baseline --prompt-version v11

traffic-bad:
	cd demo-app && $(PY) scripts/traffic.py --mode bad --requests 25 --release-id release-2026-05-26-bad-prompt --prompt-version v12

# --- deploy to Cloud Run ---

deploy: deploy-demo-app deploy-backend deploy-frontend

deploy-demo-app:
	./scripts/deploy.sh demo-app

deploy-backend:
	./scripts/deploy.sh backend

deploy-frontend:
	./scripts/deploy.sh frontend
