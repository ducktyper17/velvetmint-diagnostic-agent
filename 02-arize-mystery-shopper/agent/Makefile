.PHONY: setup seed smoke run run-sut run-loop dev test fmt lint deploy deploy-backend deploy-frontend frontend-dev

PY ?= uv run python
PORT ?= 8080

setup:
	uv sync

seed:
	$(PY) ../scripts/seed_phoenix.py

smoke:
	$(PY) -c "from qa_agent.instrumentation import setup_tracing; provider = setup_tracing(); print('phoenix tracer:', 'ok' if provider else 'skipped (no PHOENIX_API_KEY)')"

run:
	$(PY) -m qa_agent.main "Run a full audit + one improvement cycle of SUT 'velvetmint-support-v1'."

run-sut:
	@if [ -z "$$MESSAGE" ]; then echo 'usage: make run-sut MESSAGE="..."'; exit 1; fi
	$(PY) scripts/smoke_sut.py --message "$$MESSAGE"

run-loop:
	$(PY) ../scripts/run_loop.py

dev:
	$(PY) -m uvicorn qa_agent.main:app --reload --port $(PORT)

frontend-dev:
	cd ../frontend && BACKEND_URL=http://localhost:$(PORT) npm run dev

test:
	uv run pytest

fmt:
	uv run ruff format .

lint:
	uv run ruff check .
	uv run mypy .

deploy: deploy-backend deploy-frontend

deploy-backend:
	../scripts/deploy.sh backend

deploy-frontend:
	../scripts/deploy.sh frontend
