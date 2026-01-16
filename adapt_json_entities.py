# #!/usr/bin/env python3
# # adapt_json_entities.py

# import json
# import argparse
# from typing import Any, Dict, List


# def build_entities(col: int, text: str) -> List[Dict[str, str]]:
#     """
#     Правила:
#     - col=2 -> DATE
#     - col=3 -> LOC
#     - col=4 -> ORG
#     - col=5 -> MISC
#     - col=6 -> QUANTITY если есть значение, иначе []
#               "нет значения" считается: "", "-", "—"
#     - col=7 -> EVENT
#     - другие col -> []
#     """
#     text = (text or "").strip()

#     # 6-й столбец: QUANTITY только если реально есть значение (не пусто и не тире)
#     if col == 6:
#         if text in {"", "-", "—"}:
#             return []
#         return [{"text": text, "label": "QUANTITY"}]

#     if col == 2:
#         return [{"text": text, "label": "DATE"}]
#     if col == 3:
#         return [{"text": text, "label": "LOC"}]
#     if col == 4:
#         return [{"text": text, "label": "ORG"}]
#     if col == 5:
#         return [{"text": text, "label": "MISC"}]
#     if col == 7:
#         return [{"text": text, "label": "EVENT"}]

#     return []


# def adapt(obj: Dict[str, Any]) -> Dict[str, Any]:
#     if "results" not in obj or not isinstance(obj["results"], list):
#         raise ValueError("Input JSON must contain a top-level 'results' list.")

#     for cell in obj["results"]:
#         if not isinstance(cell, dict):
#             continue

#         col = cell.get("col")
#         text = cell.get("text", "")

#         # если col отсутствует/не int — пропускаем
#         if not isinstance(col, int):
#             continue

#         # работаем только со столбцами 2..7, остальные считаем несуществующими
#         if col < 2 or col > 7:
#             cell["entities"] = []
#             continue

#         cell["entities"] = build_entities(col, str(text))

#     return obj


# def main():
#     ap = argparse.ArgumentParser(description="Adapt JSON: fill entities based on col rules (2..7).")
#     ap.add_argument("in_json", help="Input JSON path")
#     ap.add_argument("-o", "--out", default="adapted.json", help="Output JSON path (default: adapted.json)")
#     args = ap.parse_args()

#     with open(args.in_json, "r", encoding="utf-8") as f:
#         obj = json.load(f)

#     obj = adapt(obj)

#     with open(args.out, "w", encoding="utf-8") as f:
#         json.dump(obj, f, ensure_ascii=False, indent=2)

#     print(f"OK: wrote {args.out}")


# if __name__ == "__main__":
#     main()


#!/usr/bin/env python3
# adapt_city_population_region.py

import json
import argparse
from typing import Any, Dict, List


NO_VALUE_MARKERS = {"", "-", "—"}


def build_entities(col: int, text: str) -> List[Dict[str, str]]:
    text = (text or "").strip()

    # col 1: Город -> LOC
    if col == 1:
        return [{"text": text, "label": "LOC"}] if text else []

    # col 2: Население -> QUANTITY (если есть значение)
    if col == 2:
        if text in NO_VALUE_MARKERS:
            return []
        return [{"text": text, "label": "QUANTITY"}]

    # col 3: Область -> GPE (если есть значение)
    if col == 3:
        if text in NO_VALUE_MARKERS:
            return []
        return [{"text": text, "label": "GPE"}]

    return []


def adapt(obj: Dict[str, Any]) -> Dict[str, Any]:
    if "results" not in obj or not isinstance(obj["results"], list):
        raise ValueError("Input JSON must contain a top-level 'results' list.")

    for cell in obj["results"]:
        if not isinstance(cell, dict):
            continue

        col = cell.get("col")
        text = cell.get("text", "")

        if not isinstance(col, int):
            cell["entities"] = []
            continue

        cell["entities"] = build_entities(col, str(text))

    return obj


def main():
    ap = argparse.ArgumentParser(
        description="Adapt JSON entities for table: City | Population | Region."
    )
    ap.add_argument("in_json", help="Input JSON path")
    ap.add_argument("-o", "--out", default="adapted.json", help="Output JSON path (default: adapted.json)")
    args = ap.parse_args()

    with open(args.in_json, "r", encoding="utf-8") as f:
        obj = json.load(f)

    obj = adapt(obj)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

    print(f"OK: wrote {args.out}")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# adapt_json_entities_roster.py

# import json
# import argparse
# from typing import Any, Dict, List


# NO_VALUE_MARKERS = {"", "-", "—"}

# SECTION_WORDS = {
#     "Вратари",
#     "Защитники",
#     "Левые крайние нападающие",
#     "Правые крайние нападающие",
#     "Центрфорварды",
# }


# def norm_text(x: Any) -> str:
#     return (str(x) if x is not None else "").strip()


# def is_no_value(text: str) -> bool:
#     return norm_text(text) in NO_VALUE_MARKERS


# def build_entities(col: int, text: str) -> List[Dict[str, str]]:
#     """
#     col=1 отсутствует
#     начинаем с col=2
#     """
#     text = norm_text(text)

#     if col < 2:
#         return []

#     # col 2: PER или MISC (для Вратари/Защитники/...)
#     if col == 2:
#         if text in SECTION_WORDS:
#             return [{"text": text, "label": "MISC"}]
#         return [{"text": text, "label": "PER"}] if text else []

#     if col == 3:
#         return [{"text": text, "label": "GPE"}] if text else []

#     if col == 4:
#         return [{"text": text, "label": "MISC"}] if text else []

#     if col == 5:
#         return [{"text": text, "label": "DATE"}] if text else []

#     if col == 6:
#         if is_no_value(text):
#             return []
#         return [{"text": text, "label": "QUANTITY"}]

#     if col == 7:
#         if is_no_value(text):
#             return []
#         return [{"text": text, "label": "QUANTITY"}]

#     if col == 8:
#         if is_no_value(text):
#             return []
#         return [{"text": text, "label": "MONEY"}]

#     if col == 9:
#         if is_no_value(text):
#             return []
#         return [{"text": text, "label": "DATE"}]

#     return []


# def adapt(obj: Dict[str, Any]) -> Dict[str, Any]:
#     if "results" not in obj or not isinstance(obj["results"], list):
#         raise ValueError("Input JSON must contain a top-level 'results' list.")

#     for cell in obj["results"]:
#         if not isinstance(cell, dict):
#             continue

#         col = cell.get("col")
#         text = cell.get("text", "")

#         if not isinstance(col, int):
#             cell["entities"] = []
#             continue

#         cell["entities"] = build_entities(col, text)

#     return obj


# def main():
#     ap = argparse.ArgumentParser(
#         description="Adapt JSON entities for hockey roster table (col starts from 2)."
#     )
#     ap.add_argument("in_json", help="Input JSON path")
#     ap.add_argument(
#         "-o", "--out", default="adapted.json", help="Output JSON path (default: adapted.json)"
#     )
#     args = ap.parse_args()

#     with open(args.in_json, "r", encoding="utf-8") as f:
#         obj = json.load(f)

#     obj = adapt(obj)

#     with open(args.out, "w", encoding="utf-8") as f:
#         json.dump(obj, f, ensure_ascii=False, indent=2)

#     print(f"OK: wrote {args.out}")


# if __name__ == "__main__":
#     main()

#py adapt_json_entities.py "data\test_set\213_locations_table.json" -o "data\test_set\213_locations_table.json"