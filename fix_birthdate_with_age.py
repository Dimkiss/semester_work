#!/usr/bin/env python3
# fix_birthdate_with_age.py

import json
import argparse
import re
from typing import Any, Dict, List


SECTION_WORDS = {
    "Вратари",
    "Защитники",
    "Левые крайние нападающие",
    "Центрфорварды",
    "Правые крайние нападающие",
}

# Пример: "29 января 1986 (35 лет)"
DATE_RE = re.compile(r"^(.+?)\s*\(")
AGE_RE = re.compile(r"\(\s*(\d+)\s*(?:лет|год|года)\s*\)")


def norm_text(x: Any) -> str:
    return (str(x) if x is not None else "").strip()


def fix(obj: Dict[str, Any]) -> Dict[str, Any]:
    if "results" not in obj or not isinstance(obj["results"], list):
        raise ValueError("Input JSON must contain a top-level 'results' list.")

    for cell in obj["results"]:
        if not isinstance(cell, dict):
            continue

        # Работаем ТОЛЬКО с колонкой "Дата рождения"
        if cell.get("col") != 5:
            continue

        text = norm_text(cell.get("text", ""))
        if not text or text in SECTION_WORDS:
            continue

        entities: List[Dict[str, str]] = []

        # 1) Дата рождения
        m_date = DATE_RE.search(text)
        if m_date:
            date_text = m_date.group(1).strip()
            entities.append(
                {"text": date_text, "label": "DATE"}
            )

        # 2) Возраст — В ФОРМАТЕ "(35 лет)"
        m_age = AGE_RE.search(text)
        if m_age:
            age_text = f"({m_age.group(1)} лет)"
            entities.append(
                {"text": age_text, "label": "QUANTITY"}
            )

        if entities:
            cell["entities"] = entities

    return obj


def main():
    ap = argparse.ArgumentParser(
        description="Fix birth date column: DATE + QUANTITY(age in '(N лет)' format)."
    )
    ap.add_argument("in_json", help="Input JSON path (must exist)")
    ap.add_argument("-o", "--out", required=True, help="Output JSON path")
    args = ap.parse_args()

    with open(args.in_json, "r", encoding="utf-8") as f:
        obj = json.load(f)

    obj = fix(obj)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

    print(f"OK: wrote {args.out}")


if __name__ == "__main__":
    main()
