# run.py
import argparse
import json
import os

from table_load import RF200TableLoader
from ner_spacy import SpacyNER


def main():
    parser = argparse.ArgumentParser(
        description="Запуск spaCy NER для таблиц RF-200 (CSV → JSON)"
    )

    # --- обязательные аргументы ---
    parser.add_argument("--tables_dir", required=True, help="Путь к директории с CSV-файлами")
    parser.add_argument("--table_id", type=int, required=True, help="Номер таблицы (например 201)")
    parser.add_argument("--out", required=True, help="Путь к выходному JSON-файлу")

    # --- опциональные аргументы ---
    parser.add_argument("--model", default="ru_core_news_lg", help="spaCy модель (по умолчанию ru_core_news_lg)")
    parser.add_argument("--quiet", action="store_true", help="Отключить вывод в консоль")

    # --- управление предобработкой таблицы ---
    parser.add_argument("--drop_first_col", choices=["auto", "true", "false"], default="auto",
                        help="Удалять ли первый столбец (нумерацию): auto | true | false")
    parser.add_argument("--drop_header", choices=["true", "false"], default="true",
                        help="Удалять ли первую строку (заголовок): true | false")

    # --- НОВОЕ: база индексации для output JSON ---
    parser.add_argument("--index_base", choices=["0", "1"], default="0",
                        help="База индексации row/col в JSON: 0 (по умолчанию) или 1")

    args = parser.parse_args()

    # --- преобразование аргументов ---
    if args.drop_first_col == "true":
        drop_first_col = True
    elif args.drop_first_col == "false":
        drop_first_col = False
    else:
        drop_first_col = None  # auto

    drop_header = args.drop_header == "true"
    index_base = int(args.index_base)  # 0 или 1

    # --- загрузка таблицы ---
    loader = RF200TableLoader(
        tables_dir=args.tables_dir,
        verbose=not args.quiet
    )

    cells = loader.load_table(
        table_id=args.table_id,
        drop_first_col=drop_first_col,
        drop_header=drop_header
    )

    if not cells:
        print("[ERROR] Таблица не загружена или пуста")
        return

    # --- инициализация spaCy ---
    ner = SpacyNER(model_name=args.model)

    # --- NER для всех ячеек ---
    results = []
    for cell in cells:
        entities = ner.extract_entities(cell["text"])
        entities_clean = [{"text": e["text"], "label": e["label"]} for e in entities]

        r = int(cell["row"])
        c = int(cell["col"])

        # если хотим 1-based — сдвигаем
        if index_base == 1:
            r += 1
            c += 1

        results.append({
            "row": r,
            "col": c,
            "text": cell["text"],
            "entities": entities_clean
        })

    table_file = loader._find_table_file(args.table_id)
    output_obj = {
        "table_name": os.path.basename(table_file) if table_file else f"{args.table_id}.csv",
        "method": "spacy",
        "meta": {
            "drop_header": drop_header,
            "drop_first_col": drop_first_col,
            "index_base": index_base,
        },
        "results": results
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output_obj, f, ensure_ascii=False, indent=2)

    if not args.quiet:
        print(f"[OK] Ячеек обработано: {len(results)}")
        print(f"[OK] Результат сохранён: {args.out}")


if __name__ == "__main__":
    main()
