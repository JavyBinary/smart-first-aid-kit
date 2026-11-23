# 020-bm25-core-corpus-and-benchmark: Инженерный план реализации

## 1. Модуль предобработки текстов (`backend/src/medai/rag/analyzer.py`)
1. Реализовать `normalize_text(text: str) -> str` (NFC, casefold, whitespace collapse, `ё` $\rightarrow$ `е`).
2. Скомпилировать регулярное выражение токенизации `[a-zа-я0-9]+(?:-[a-zа-я0-9]+)*`.
3. Реализовать абстрактный класс `TextAnalyzer` и реализации `SimpleAnalyzer` и `MorphAnalyzer` (с `pymorphy3`).

## 2. Реализация математического аппарата BM25 (`backend/src/medai/rag/bm25.py`)
1. Класс параметров `Bm25Params` ($k_1 = 1.5, b = 0.75$).
2. Функция `idf(n_documents, document_frequency)`.
3. Функция `term_score(tf, doc_len, avgdl, params)`.
4. Функция ранжирования `score(query_terms, postings, lengths, n_documents, avgdl, params) -> dict[str, float]`.
5. Функция сортировки `rank(scores, top_k) -> tuple[str, ...]`.

## 3. Инвертированный индекс и загрузка (`backend/src/medai/rag/index.py`, `package.py`)
1. Модели `MedicineDocument`, `MedicinePackage` на Pydantic v2.
2. Реализация `InMemoryBm25Index` (постинг-листы, длины документов, метаданные).
3. Функция `load_package(path: Path, analyzer: TextAnalyzer) -> InMemoryBm25Index`.

## 4. Формирование медицинского корпуса и бенчмарк-запросов
1. Создать `data/medicines/package.yaml` с 30 официальными препаратами (`D01`–`D30`).
2. Создать `data/benchmark_queries.yaml` с 15 контрольными сценариями (10 симптоматических + 5 ловушек).

## 5. Модуль бенчмаркинга (`backend/src/medai/rag/benchmark.py`)
1. Pydantic-модели `BenchmarkQuestion`, `BenchmarkSet`, `BenchmarkReport`.
2. Класс `BenchmarkRunner` с замером latency, расчетом $MRR$, $Recall@1$, $Recall@3$, $Recall@5$ и Correct Rejection Rate.
3. Консольный вывод и форматирование результатов.

## 6. Актуализация `Makefile`
1. Добавить фасадные цели `make bench` и `make knowledge-load`.

## 7. Тестирование и верификация
1. Написать модульные тесты в `backend/tests/test_bm25.py` и `backend/tests/test_benchmark.py`.
2. Запустить `make bench`, `make test`, `make lint`.
3. Зафиксировать терминальные доказательства в `verification.md` и перевести спецификацию в статус `done`.
