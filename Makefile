.PHONY: help up down restart logs build shell-backend migrate test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Docker ───────────────────────────────────────────────────────────────────
up: ## Start all services
	docker-compose up --build -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## Tail logs from all services
	docker-compose logs -f

logs-backend: ## Tail backend logs only
	docker-compose logs -f backend

build: ## Rebuild all Docker images
	docker-compose build --no-cache

# ─── Shell Access ─────────────────────────────────────────────────────────────
shell-backend: ## Open shell in backend container
	docker-compose exec backend bash

shell-db: ## Open psql in postgres container
	docker-compose exec postgres psql -U fiscalmind -d fiscalmind_db

# ─── Database ─────────────────────────────────────────────────────────────────
migrate: ## Run Alembic migrations
	docker-compose exec backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="add user table")
	docker-compose exec backend alembic revision --autogenerate -m "$(msg)"

migrate-downgrade: ## Rollback last migration
	docker-compose exec backend alembic downgrade -1

# ─── Testing ──────────────────────────────────────────────────────────────────
test: ## Run all tests
	docker-compose exec backend pytest tests/ -v --cov=app --cov-report=term-missing

# ─── Cleanup ──────────────────────────────────────────────────────────────────
clean: ## Remove all containers, volumes, and images
	docker-compose down -v --rmi local
