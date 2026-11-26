"""CLI entrypoint for MedAI RAG management: check, load, export, delete, restore, search."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import yaml

from medai.config import load_config
from medai.db.engine import create_engine
from medai.rag.analyzer import MorphAnalyzer
from medai.rag.index import find_data_dir, load_package_from_yaml
from medai.rag.postgres import PostgresRagStore


async def _cmd_load(pkg_path: Path, output_json: bool) -> int:
    cfg = load_config()
    engine = create_engine(cfg.database)
    try:
        store = PostgresRagStore(engine)
        summary = await store.replace_from_yaml(pkg_path)
    finally:
        await engine.dispose()

    payload = {
        "status": "ok",
        "load_id": summary.load_id,
        "documents": summary.document_count,
        "chunks": summary.chunk_count,
        "terms": summary.term_count,
    }
    if output_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(
            f"Загружено: {summary.document_count} препаратов, "
            f"{summary.chunk_count} чанков, {summary.term_count} термов."
        )
    return 0


async def _cmd_export(out_dir: Path) -> int:
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"Ошибка: каталог {out_dir} не пуст.", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    engine = create_engine(cfg.database)
    try:
        store = PostgresRagStore(engine)
        pkg = await store.export_package()
    finally:
        await engine.dispose()

    target = out_dir / "package.yaml"
    with open(target, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            pkg.model_dump(mode="json"),
            f,
            allow_unicode=True,
            sort_keys=False,
        )
    print(f"Экспортировано {len(pkg.medicines)} препаратов в {target}")
    return 0


async def _cmd_delete(doc_ids: list[str]) -> int:
    cfg = load_config()
    engine = create_engine(cfg.database)
    try:
        store = PostgresRagStore(engine)
        deleted_count = 0
        for doc_id in doc_ids:
            if await store.delete_medicine(doc_id):
                deleted_count += 1
        print(f"Удалено документов: {deleted_count}")
        return 0
    finally:
        await engine.dispose()


async def _cmd_restore(doc_id: str, revision: int | None) -> int:
    cfg = load_config()
    engine = create_engine(cfg.database)
    try:
        store = PostgresRagStore(engine)
        restored = await store.restore_revision(doc_id, revision=revision)
        if restored is None:
            print(f"Ревизия для {doc_id} не найдена.", file=sys.stderr)
            return 1
        print(f"Восстановлен препарат {restored.id}: {restored.title}")
        return 0
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m medai.rag")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Validate YAML package without DB")
    p_check.add_argument("dir", type=Path)

    p_load = sub.add_parser("load", help="Validate and load package into PostgreSQL")
    p_load.add_argument("dir", type=Path)
    p_load.add_argument("--json", action="store_true")

    p_export = sub.add_parser("export", help="Export PostgreSQL knowledge to YAML")
    p_export.add_argument("dir", type=Path)

    p_del = sub.add_parser("delete", help="Delete medicines by ID")
    p_del.add_argument("ids", nargs="+")

    p_rest = sub.add_parser("restore", help="Restore medicine from revision log")
    p_rest.add_argument("id")
    p_rest.add_argument("--revision", type=int, default=None)

    p_search = sub.add_parser("search", help="Search local YAML corpus")
    p_search.add_argument("query")
    p_search.add_argument("--top-k", type=int, default=5)

    args = parser.parse_args(argv)

    if args.command == "check":
        pkg_path = args.dir / "package.yaml" if args.dir.is_dir() else args.dir
        idx = load_package_from_yaml(pkg_path, MorphAnalyzer())
        print(f"Пакет валиден: {idx.document_count} препаратов.")
        return 0
    if args.command == "load":
        pkg_path = args.dir / "package.yaml" if args.dir.is_dir() else args.dir
        return asyncio.run(_cmd_load(pkg_path, args.json))
    if args.command == "export":
        return asyncio.run(_cmd_export(args.dir))
    if args.command == "delete":
        return asyncio.run(_cmd_delete(args.ids))
    if args.command == "restore":
        return asyncio.run(_cmd_restore(args.id, args.revision))
    if args.command == "search":
        pkg_path = find_data_dir() / "medicines" / "package.yaml"
        analyzer = MorphAnalyzer()
        idx = load_package_from_yaml(pkg_path, analyzer)
        for res in idx.search(analyzer.terms(args.query), top_k=args.top_k):
            print(f"{res.doc_id} | {res.score:.3f} | {res.title}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
