.PHONY: test lint typecheck dev backend-test frontend-test

test: backend-test frontend-test

backend-test:
	cd backend && python -m pytest -q

frontend-test:
	cd frontend && npx --yes pnpm@9.15.4 test -- --run

lint:
	cd backend && python -m ruff check src tests
	cd frontend && npx --yes pnpm@9.15.4 lint

typecheck:
	cd backend && python -m mypy src
	cd frontend && npx --yes pnpm@9.15.4 typecheck

dev:
	docker compose up --build
