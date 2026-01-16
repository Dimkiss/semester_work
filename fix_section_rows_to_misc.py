#!/usr/bin/env python3
# fix_section_rows_to_misc.py

import json
import argparse
from typing import Any, Dict, List


SECTION_WORDS = {
    "Вратари",
    "Защитники",
    "Левые крайние нападающие",
    "Центрфорварды",
    "Правые крайние нападающие",
}


def norm_text(x: Any) -> str:
    return (str(x) if x is not None else "").strip()


def fix(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Для всех ячеек, у которых text входит в SECTION_WORDS,
    выставляет entities = [{"text": text, "label": "MISC"}].
    """
    if "results" not in obj or not isinstance(obj["results"], list):
        raise ValueError("Input JSON must contain a top-level 'results' list.")

    for cell in obj["results"]:
        if not isinstance(cell, dict):
            continue

        text = norm_text(cell.get("text", ""))
        if text in SECTION_WORDS:
            cell["entities"] = [{"text": text, "label": "MISC"}]

    return obj


def main():
    ap = argparse.ArgumentParser(description="Force section header cells to MISC entities.")
    ap.add_argument("in_json", help="Input JSON path")
    ap.add_argument("-o", "--out", default="fixed.json", help="Output JSON path (default: fixed.json)")
    args = ap.parse_args()

    with open(args.in_json, "r", encoding="utf-8") as f:
        obj = json.load(f)

    obj = fix(obj)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

    print(f"OK: wrote {args.out}")


if __name__ == "__main__":
    main()
