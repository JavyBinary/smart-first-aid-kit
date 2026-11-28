#!/usr/bin/env python3
"""
Скрипт проверки бенчмарка Смешариков (15 вопросов).
Отправляет каждый вопрос в отдельном запросе и формирует таблицу:
ID | Вопрос | Ответ системы | Документы (топ-3)
"""
import json
import os
import sys
import urllib.request
import urllib.error

BASE_URL = os.environ.get("MEDAI_URL", "http://localhost:8090")
ENDPOINT = f"{BASE_URL}/api/v1/chat/query"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
QUESTIONS_FILE = os.path.join(REPO_DIR, "data", "smeshariki", "questions.json")

def main():
    if not os.path.exists(QUESTIONS_FILE):
        print(f"Файл с вопросами не найден: {QUESTIONS_FILE}")
        sys.exit(1)

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"\n🚀 Запуск бенчмарка Смешариков ({len(questions)} вопросов)...")
    print(f"Сервер: {ENDPOINT}\n")

    results = []

    for item in questions:
        qid = item["id"]
        qtext = item["question"]

        payload = json.dumps({
            "query": qtext,
            "include_kit_context": False,
            "user_kit_names": [],
            "user_kit_items": [],
            "selected_pills": [],
            "health_profile": None,
            "response_depth": "brief"
        }).encode("utf-8")

        req = urllib.request.Request(
            ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg = data.get("message", "").strip()
                sources = data.get("sources", [])

                doc_ids = []
                for s in sources:
                    did = s.get("id") or s.get("doc_id") or s.get("document_id")
                    if did and did not in doc_ids:
                        doc_ids.append(did)

                # Fallback: parse document tags like [D07] from message if sources empty
                if not doc_ids:
                    import re
                    found = re.findall(r"\[(D\d{2})\]", msg)
                    for f in found:
                        if f not in doc_ids:
                            doc_ids.append(f)

                results.append({
                    "id": qid,
                    "question": qtext,
                    "answer": msg,
                    "retrieved_documents": doc_ids[:3]
                })
                print(f"  ✓ {qid}: найдено документов: {doc_ids[:3]}")

        except Exception as e:
            print(f"  ✗ {qid}: Ошибка запроса ({e})")
            results.append({
                "id": qid,
                "question": qtext,
                "answer": f"Ошибка: {e}",
                "retrieved_documents": []
            })

    # Сохраняем JSON
    out_json = os.path.join(REPO_DIR, "data", "smeshariki", "benchmark_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Вывод Markdown таблицы
    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТЫ БЕНЧМАРКА")
    print("=" * 80 + "\n")

    md_lines = [
        "| ID | Вопрос | Ответ системы | Документы (топ-3) |",
        "|---|---|---|---|"
    ]

    for r in results:
        qid = r["id"]
        q = r["question"]
        ans = r["answer"].replace("\n", " ").replace("|", "/")
        if len(ans) > 120:
            ans = ans[:117] + "..."
        docs = ", ".join(r["retrieved_documents"]) if r["retrieved_documents"] else "нет"
        md_lines.append(f"| **{qid}** | {q} | {ans} | {docs} |")

    table_md = "\n".join(md_lines)
    print(table_md)

    out_md = os.path.join(REPO_DIR, "data", "smeshariki", "benchmark_results.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(table_md + "\n")

    print(f"\nРезультаты сохранены:")
    print(f"  - {out_json}")
    print(f"  - {out_md}\n")

if __name__ == "__main__":
    main()
