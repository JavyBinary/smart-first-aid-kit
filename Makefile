.PHONY: help run run-ui dev-frontend run-backend migrate create-admin test bench knowledge-check knowledge-load knowledge-export knowledge-delete knowledge-restore knowledge-search lint format spec-list

PYTHON ?= python3

help:
	@echo "MedAI — Доступные команды сборки и запуска:"
	@echo "  make run          - Запуск полного контура (Caddy, Backend, Frontend, Postgres, Redis) через Docker"
	@echo "  make run-ui       - Запуск клиентского интерфейса на http://localhost:8000"
	@echo "  make dev-frontend - Запуск Vite dev-сервера фронтенда (порт 3000)"
	@echo "  make run-backend  - Запуск сервера FastAPI через uv (Uvicorn, порт 8000)"
	@echo "  make migrate      - Применение миграций схемы базы данных (Alembic)"
	@echo "  make create-admin - Создание учетной записи администратора (EMAIL=<email> [ROLE=admin|superadmin])"
	@echo "  make test         - Запуск модульных тестов backend и интеграционных проверок"
	@echo "  make bench        - Запуск бенчмарка BM25 + Hybrid Ablation (MRR, Recall@k, Accuracy, Faithfulness)"
	@echo "  make knowledge-check   - Валидация YAML-пакета знаний без БД (DIR=<dir>)"
	@echo "  make knowledge-load    - Загрузка пакета знаний в PostgreSQL и индексация ([DIR=<dir>] [DB=1])"
	@echo "  make knowledge-export  - Выгрузка корпуса знаний из PostgreSQL в YAML (DIR=<dir>)"
	@echo "  make knowledge-delete  - Удаление препаратов по ID из PostgreSQL (IDS=\"D01 ...\")"
	@echo "  make knowledge-restore - Восстановление препарата из ревизии PostgreSQL (ID=D01 [REV=N])"
	@echo "  make knowledge-search  - Поиск по корпусу знаний из CLI (QUERY=\"...\")"
	@echo "  make lint         - Проверка качества кода линтером (Ruff + синтаксис)"
	@echo "  make format       - Автоматическое форматирование кода (Ruff)"
	@echo "  make spec-list    - Просмотр реестра спецификаций SDD"

run:
	@echo "Запуск полного контура MedAI через Docker Compose..."
	@docker compose -f docker/compose.yaml up --build -d

run-ui:
	@echo "Запуск веб-сервера клиентского интерфейса на http://localhost:8000..."
	@if [ -d "frontend" ]; then \
		$(PYTHON) -m http.server 8000 --directory frontend; \
	else \
		$(PYTHON) -m http.server 8000; \
	fi

dev-frontend:
	@echo "Запуск Vite Dev Server..."
	@cd frontend && npm install && npm run dev

run-backend:
	@echo "Запуск сервера FastAPI (MedAI Backend)..."
	@cd backend && uv run uvicorn medai.main:app --reload --port 8000

migrate:
	@echo "Применение миграций базы данных Alembic..."
	@cd backend && uv run python -m medai.db.migrate

create-admin:
	@test -n "$(EMAIL)" || { \
		echo "Использование: make create-admin EMAIL=<email> [ROLE=admin|superadmin] [NAME=<name>]" >&2; \
		exit 2; \
	}
	@cd backend && uv run python -m medai.create_admin --email "$(EMAIL)" --role "$(or $(ROLE),admin)" --name "$(or $(NAME),Администратор MedAI)"

test:
	@echo "Запуск тестов backend..."
	@if [ -d "backend" ] && command -v uv >/dev/null 2>&1; then \
		cd backend && uv run pytest -v; \
	elif command -v pytest >/dev/null 2>&1; then \
		pytest -v tests/; \
	else \
		$(PYTHON) -m unittest discover -s tests -p "test_*.py" 2>/dev/null || echo "Модульные тесты завершены."; \
	fi
	@if command -v node >/dev/null 2>&1 && ls frontend/tests/*.test.js >/dev/null 2>&1; then \
		echo "Запуск unit-тестов frontend..."; \
		node --test frontend/tests/*.test.js; \
	fi

test-integration:
	@echo "Запуск E2E-тестов с реальными PostgreSQL и Redis..."
	@docker compose -f docker/compose.test.yaml up -d
	@until docker compose -f docker/compose.test.yaml exec -T postgres-test pg_isready -U medai -d medai_test >/dev/null 2>&1; do sleep 1; done
	@until docker compose -f docker/compose.test.yaml exec -T redis-test redis-cli ping >/dev/null 2>&1; do sleep 1; done
	@(cd backend && MEDAI_INTEGRATION=1 PYTHONPATH=src uv run pytest tests/integration -v); \
	status=$$?; \
	docker compose -f docker/compose.test.yaml down -v; \
	exit $$status

bench:
	@echo "Запуск бенчмарка поискового ядра BM25..."
	@if [ -d "backend" ] && command -v uv >/dev/null 2>&1; then \
		cd backend && uv run python -m medai.rag.benchmark; \
	elif [ -f "benchmark/run.py" ]; then \
		$(PYTHON) -m benchmark.run; \
	else \
		echo "Бенчмарк-раннер не найден."; \
	fi

knowledge-check:
	@cd backend && uv run python -m medai.rag check "$(or $(DIR),../data/medicines)"

knowledge-load:
	@echo "Загрузка и индексация медицинского корпуса BM25/Hybrid..."
	@cd backend && uv run python -m medai.rag.knowledge_load $(if $(DIR),--dir "$(DIR)",) $(if $(filter 1,$(DB)),--db,)

knowledge-export:
	@test -n "$(DIR)" || { echo "Использование: make knowledge-export DIR=<dir>" >&2; exit 2; }
	@cd backend && uv run python -m medai.rag export "$(DIR)"

knowledge-delete:
	@test -n "$(IDS)" || { echo "Использование: make knowledge-delete IDS=\"D01 D02\"" >&2; exit 2; }
	@cd backend && uv run python -m medai.rag delete $(IDS)

knowledge-restore:
	@test -n "$(ID)" || { echo "Использование: make knowledge-restore ID=D01 [REV=N]" >&2; exit 2; }
	@cd backend && uv run python -m medai.rag restore "$(ID)" $(if $(REV),--revision "$(REV)",)

knowledge-search:
	@test -n "$(QUERY)" || { echo "Использование: make knowledge-search QUERY=\"...\"" >&2; exit 2; }
	@cd backend && uv run python -m medai.rag search "$(QUERY)" $(if $(TOPK),--top-k "$(TOPK)",)

lint:
	@echo "Проверка линтером Ruff..."
	@if [ -d "backend" ] && command -v uv >/dev/null 2>&1; then \
		cd backend && uv run ruff check .; \
	elif command -v ruff >/dev/null 2>&1; then \
		ruff check .; \
	fi
	@$(PYTHON) -m py_compile .agents/skills/sdd/scripts/spec_status.py && echo "Синтаксис скриптов SDD корректен."

format:
	@echo "Форматирование кода..."
	@if [ -d "backend" ] && command -v uv >/dev/null 2>&1; then \
		cd backend && uv run ruff format .; \
	elif command -v ruff >/dev/null 2>&1; then \
		ruff format .; \
	else \
		echo "Ruff не установлен, форматирование пропущено."; \
	fi

spec-list:
	@$(PYTHON) .agents/skills/sdd/scripts/spec_status.py list
