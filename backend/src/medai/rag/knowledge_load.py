"""CLI script to load, validate, and persist medical knowledge package into PostgreSQL + BM25."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from medai.config import load_config
from medai.db.engine import create_engine
from medai.rag.analyzer import MorphAnalyzer
from medai.rag.index import find_data_dir, load_package_from_yaml
from medai.rag.postgres import PostgresRagStore


async def _persist_to_db(target_path: Path) -> None:
    cfg = load_config()
    engine = create_engine(cfg.database)
    try:
        store = PostgresRagStore(engine)
        summary = await store.replace_from_yaml(target_path)
        print(
            f"Загружено в PostgreSQL (load_id={summary.load_id}): "
            f"{summary.document_count} препаратов, {summary.chunk_count} чанков, "
            f"{summary.term_count} уникальных термов."
        )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load and validate medical knowledge package."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Path to package.yaml file",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Directory containing package.yaml",
    )
    parser.add_argument(
        "--db",
        action="store_true",
        help="Persist documents, chunks, embeddings, and BM25 index into PostgreSQL",
    )
    args = parser.parse_args()

    data_dir = find_data_dir()

    target_path = args.path
    if not target_path and args.dir:
        target_path = args.dir / "package.yaml"
    if not target_path:
        target_path = data_dir / "medicines" / "package.yaml"

    if not target_path.exists():
        print(f"Ошибка: файл пакета знаний не найден: {target_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Загрузка пакета знаний: {target_path}...")
    analyzer = MorphAnalyzer()
    index = load_package_from_yaml(target_path, analyzer)
    print(
        f"Успешно загружено и проиндексировано {index.document_count} препаратов. "
        f"Средняя длина документа: {index.average_length:.1f} термов."
    )

    if args.db:
        asyncio.run(_persist_to_db(target_path))


if __name__ == "__main__":
    main()
