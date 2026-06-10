.PHONY: test lint typecheck dev backend-test frontend-test

test: backend-test frontend-test

backend-test:
	cd backend && python -m pytest -q

frontend-test:
	cd frontend && pnpm test -- --run

lint:
	cd backend && python -m ruff check src tests
	cd frontend && pnpm lint

typecheck:
	cd backend && python -m mypy src
	cd frontend && pnpm typecheck

dev:
	docker compose up --build