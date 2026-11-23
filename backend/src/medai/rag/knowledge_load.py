"""CLI script to load and validate medical knowledge package into BM25 index."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from medai.rag.analyzer import MorphAnalyzer
from medai.rag.index import load_package_from_yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and validate medical knowledge package.")
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
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[4]
    if not (root / "data").exists():
        root = Path.cwd()
        if (root / "backend").exists() and not (root / "data").exists():
            root = root.parent

    target_path = args.path
    if not target_path and args.dir:
        target_path = args.dir / "package.yaml"
    if not target_path:
        target_path = root / "data" / "medicines" / "package.yaml"

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


if __name__ == "__main__":
    main()
