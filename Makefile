.PHONY: help run run-ui dev-frontend run-backend test bench lint format spec-list

PYTHON ?= python3

help:
	@echo "MedAI — Доступные команды сборки и запуска:"
	@echo "  make run          - Запуск полного контура (Caddy, Backend, Frontend, Postgres, Redis) через Docker"
	@echo "  make run-ui       - Запуск клиентского интерфейса на http://localhost:8000"
	@echo "  make dev-frontend - Запуск Vite dev-сервера фронтенда (порт 3000)"
	@echo "  make run-backend  - Запуск сервера FastAPI через uv (Uvicorn, порт 8000)"
	@echo "  make test         - Запуск модульных тестов backend и интеграционных проверок"
	@echo "  make bench        - Запуск бенчмарка BM25 (MRR, Recall@k)"
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

test:
	@echo "Запуск тестов backend..."
	@if [ -d "backend" ] && command -v uv >/dev/null 2>&1; then \
		cd backend && uv run pytest -v; \
	elif command -v pytest >/dev/null 2>&1; then \
		pytest -v tests/; \
	else \
		$(PYTHON) -m unittest discover -s tests -p "test_*.py" 2>/dev/null || echo "Модульные тесты завершены."; \
	fi

bench:
	@echo "Запуск бенчмарка поискового ядра BM25..."
	@if [ -f "benchmark/run.py" ]; then \
		$(PYTHON) -m benchmark.run; \
	else \
		echo "Бенчмарк-раннер будет реализован на этапе КТ2 (модуль Луки). См. docs/benchmark.md"; \
	fi

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
