import argparse
import json
import os
from typing import Any, Dict, Tuple

from nel_wikidata import EntityLinker, is_russian

LINK_LABELS = {"LOC", "GPE", "PER", "PERSON", "ORG", "ORGANIZATION"}


def load_json(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, obj: Dict[str, Any]):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def add_nel(obj: Dict[str, Any], linker: EntityLinker) -> Tuple[int, int, int]:
    linked = 0
    attempted = 0
    total = 0

    for cell in obj.get("results", []):
        entities = cell.get("entities") or []
        for ent in entities:
            total += 1
            label = (ent.get("label") or "").upper()
            text = (ent.get("text") or "").strip()

            if label not in LINK_LABELS:
                ent["kb_id"] = None
                continue

            if not is_russian(text):
                ent["kb_id"] = None
                continue

            attempted += 1
            kb_id = linker.search_wikidata(text)
            ent["kb_id"] = kb_id
            if kb_id:
                linked += 1

    return linked, attempted, total


def main():
    p = argparse.ArgumentParser(description="NEL: добавить ссылки Wikidata к сущностям из NER-json")
    p.add_argument("--in_ner", required=True, help="входной JSON после NER")
    p.add_argument("--out", required=True, help="выходной JSON (NER+NEL)")
    p.add_argument("--limit", type=int, default=1, help="сколько кандидатов брать из Wikidata")
    p.add_argument("--sleep", type=float, default=0.05, help="пауза между запросами (сек)")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    obj = load_json(args.in_ner)

    linker = EntityLinker(limit=args.limit, sleep_s=args.sleep)
    linked, attempted, total = add_nel(obj, linker)

    obj["nel"] = {
        "kb": "wikidata",
        "linked": linked,
        "attempted": attempted,
        "total": total,
        "limit": args.limit,
    }

    save_json(args.out, obj)

    if not args.quiet:
        print(f"[OK] Linked {linked}/{attempted} (attempted), total entities {total}")
        print(f"[OK] Saved: {args.out}")


if __name__ == "__main__":
    main()
