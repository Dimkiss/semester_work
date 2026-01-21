import argparse
import json
import os
from typing import Any, Dict

from nel_wikidata import WikidataNEL


def load_json(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, obj: Dict[str, Any]):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def add_nel(obj: Dict[str, Any], linker: WikidataNEL, limit: int) -> Dict[str, Any]:
    linked = 0
    total = 0

    for cell in obj.get("results", []):
        entities = cell.get("entities") or []
        for ent in entities:
            total += 1
            text = ent.get("text", "") or ""
            kb_id = linker.search_wikidata(text, limit=limit)
            ent["kb_id"] = kb_id
            if kb_id:
                linked += 1

    obj["nel"] = {
        "kb": "wikidata",
        "linked": linked,
        "total": total,
        "limit": limit,
    }
    return obj


def main():
    p = argparse.ArgumentParser(description="NEL: добавить ссылки Wikidata к сущностям из NER-json")
    p.add_argument("--in_ner", required=True, help="Входной JSON от NER (spacy/zero/few)")
    p.add_argument("--out", required=True, help="Выходной JSON (NER+NEL)")
    p.add_argument("--limit", type=int, default=5, help="Сколько кандидатов смотреть в wbsearchentities")
    p.add_argument("--sleep", type=float, default=0.05, help="Пауза между запросами (сек)")
    p.add_argument("--timeout", type=float, default=10.0, help="Timeout http (сек)")
    p.add_argument("--quiet", action="store_true", help="Не печатать статистику")

    args = p.parse_args()

    obj = load_json(args.in_ner)

    with WikidataNEL(language="ru", sleep_s=args.sleep, timeout_s=args.timeout) as linker:
        out_obj = add_nel(obj, linker, limit=args.limit)

    save_json(args.out, out_obj)

    if not args.quiet:
        nel_info = out_obj.get("nel", {})
        print(f"[OK] Linked {nel_info.get('linked', 0)}/{nel_info.get('total', 0)}")
        print(f"[OK] Saved: {args.out}")


if __name__ == "__main__":
    main()
