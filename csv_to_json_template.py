# csv_to_json_template.py
#!/usr/bin/env python3
# csv_to_json_template.py

import csv
import json
import argparse
import re
from typing import List, Optional


# Под нумерацию подойдут: 1, 1., 1.0, 10.0, 001, " 3.0 "
NUMBERING_RE = re.compile(r"^\s*\d+(?:\.\d+)?\.?\s*$")


def is_numbering_value(s: Optional[str]) -> bool:
    if s is None:
        return False
    s = str(s).strip()
    if s == "":
        return False
    return bool(NUMBERING_RE.match(s))


def should_drop_first_column_as_numbering(rows: List[List[str]], threshold: float = 0.7) -> bool:
    """
    Эвристика: если в первом столбце много значений, похожих на нумерацию, считаем его "номерами".
    threshold=0.7 => 70% непустых значений должны выглядеть как номера.
    """
    if not rows:
        return False
    first_col = [r[0] if len(r) > 0 else "" for r in rows]
    non_empty = [v for v in first_col if str(v).strip() != ""]
    if len(non_empty) < 2:
        return False
    ok = sum(1 for v in non_empty if is_numbering_value(v))
    return (ok / len(non_empty)) >= threshold


def read_csv(path: str, delimiter: str, encoding: str) -> List[List[str]]:
    with open(path, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        return [row for row in reader]


def main():
    ap = argparse.ArgumentParser(
        description="Convert CSV to JSON template; drop header row and optionally drop numbering column."
    )
    ap.add_argument("csv_path", help="Path to input CSV")
    ap.add_argument("-o", "--out", default="out.json", help="Output JSON path (default: out.json)")
    ap.add_argument("-t", "--table-name", default="string", help='Value for "table_name" (default: "string")')
    ap.add_argument("-d", "--delimiter", default="|", help="CSV delimiter (default: |)")
    ap.add_argument("-e", "--encoding", default="utf-8", help="File encoding (default: utf-8)")

    # Переключатель удаления 1-го столбца
    ap.add_argument(
        "--drop-first-col",
        choices=["auto", "yes", "no"],
        default="auto",
        help="Drop first column: auto|yes|no (default: auto).",
    )
    ap.add_argument(
        "--numbering-threshold",
        type=float,
        default=0.7,
        help="When --drop-first-col=auto, ratio of numbering-like cells to drop (default: 0.7).",
    )

    # ВАЖНО: index-base теперь трактуем как "база координат исходной таблицы"
    # (обычно 1). При удалении заголовка/первого столбца координаты смещаем.
    ap.add_argument(
        "--index-base",
        type=int,
        choices=[0, 1],
        default=1,
        help="Row/col indexing base for ORIGINAL table coords (0 or 1). Default: 1",
    )

    args = ap.parse_args()

    raw = read_csv(args.csv_path, args.delimiter, args.encoding)

    # Флаги удаления для корректного смещения координат
    dropped_header = False
    drop_col = False

    # 1) Удаляем первую строку (заголовок) — как и просили всегда
    if raw:
        raw = raw[1:]
        dropped_header = True
    else:
        raw = []

    # Нормализуем ширину таблицы (чтобы у всех строк было одинаковое число колонок)
    max_cols = max((len(r) for r in raw), default=0)
    data = [r + [""] * (max_cols - len(r)) for r in raw]

    # 2) Удаляем 1-й столбец по переключателю
    if max_cols > 0:
        if args.drop_first_col == "yes":
            drop_col = True
        elif args.drop_first_col == "no":
            drop_col = False
        else:  # auto
            drop_col = should_drop_first_column_as_numbering(data, threshold=args.numbering_threshold)

    if drop_col and max_cols > 0:
        data = [r[1:] for r in data]
        max_cols = max(0, max_cols - 1)

    # 3) Смещения координат относительно ИСХОДНОЙ таблицы
    # Если base=1: заголовок занимал row=1 => первая строка данных начнётся с row=2
    # Если base=0: заголовок занимал row=0 => первая строка данных начнётся с row=1
    row_shift = 1 if dropped_header else 0
    col_shift = 1 if drop_col else 0

    base = args.index_base
    results = []

    for r_i, row in enumerate(data):
        for c_i, cell in enumerate(row):
            results.append(
                {
                    "row": r_i + base + row_shift,
                    "col": c_i + base + col_shift,
                    "text": cell.strip() if isinstance(cell, str) else "",
                    "entities": [],
                }
            )

    out_obj = {
        "table_name": args.table_name,
        "method": "manual",  # фиксированное значение
        "results": results,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

    print(
        "OK: wrote {out} | rows={rows} cols={cols} results={n} | "
        "dropped_header={dh} drop_first_col={dc} | shifts: row+{rs} col+{cs}".format(
            out=args.out,
            rows=len(data),
            cols=max_cols,
            n=len(results),
            dh=dropped_header,
            dc=drop_col,
            rs=row_shift,
            cs=col_shift,
        )
    )


if __name__ == "__main__":
    main()

#py csv_to_json_template.py "data\all_tables\212_sports_table.csv" -o "data\test_set\212_sports_table.json" --drop-first-col yes
#py csv_to_json_template.py "data\all_tables\213_locations_table.csv" -o "data\test_set\213_locations_table.json" --drop-first-col no