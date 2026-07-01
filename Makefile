.PHONY: dev-backend dev-frontend test lint format build-frontend

# Run the API with hot reload (http://localhost:8000)
dev-backend:
	cd backend && uvicorn app.main:create_app --factory --reload --port 8000

# Run the Vite dev server (http://localhost:5173, proxies /api to :8000)
dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest

lint:
	cd backend && ruff check . && ruff format --check .

format:
	cd backend && ruff format .

build-frontend:
	cd frontend && npm run build
