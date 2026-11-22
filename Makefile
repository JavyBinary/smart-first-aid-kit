.PHONY: help run-ui run-backend test bench lint format spec-list

PYTHON ?= python3

help:
	@echo "MedAI — Доступные команды сборки и запуска:"
	@echo "  make run-ui       - Запуск веб-сервера интерфейса (порт 8000)"
	@echo "  make run-backend  - Запуск сервера FastAPI (Uvicorn, порт 8000)"
	@echo "  make test         - Запуск модульных тестов"
	@echo "  make bench        - Запуск бенчмарка BM25 (MRR, Recall@k)"
	@echo "  make lint         - Проверка качества кода линтером"
	@echo "  make format       - Автоматическое форматирование кода"
	@echo "  make spec-list    - Просмотр реестра спецификаций SDD"

run-ui:
	@echo "Запуск прототипа клиентского интерфейса на http://localhost:8000/ui/auth.html..."
	$(PYTHON) -m http.server 8000

run-backend:
	@echo "Запуск сервера FastAPI..."
	@if [ -f "backend/src/main.py" ]; then \
		uvicorn backend.src.main:app --reload --port 8000; \
	elif [ -f "app/main.py" ]; then \
		uvicorn app.main:app --reload --port 8000; \
	else \
		echo "Ошибка: серверный модуль FastAPI еще не развернут (модуль Полины)."; \
		exit 1; \
	fi

test:
	@echo "Запуск тестов..."
	@if command -v pytest >/dev/null 2>&1; then \
		pytest -v tests/; \
	else \
		$(PYTHON) -m unittest discover -s tests -p "test_*.py" || echo "Тесты будут добавлены на этапе КТ2."; \
	fi

bench:
	@echo "Запуск бенчмарка поискового ядра BM25..."
	@if [ -f "benchmark/run.py" ]; then \
		$(PYTHON) -m benchmark.run; \
	else \
		echo "Бенчмарк-раннер будет реализован на этапе КТ2 (модуль Луки). См. docs/benchmark.md"; \
	fi

lint:
	@echo "Проверка линтером..."
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check .; \
	else \
		$(PYTHON) -m py_compile .agents/skills/sdd/scripts/spec_status.py && echo "Синтаксис скриптов корректен."; \
	fi

format:
	@echo "Форматирование кода..."
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format .; \
	else \
		echo "Ruff не установлен, форматирование пропущено."; \
	fi

spec-list:
	@$(PYTHON) .agents/skills/sdd/scripts/spec_status.py list
