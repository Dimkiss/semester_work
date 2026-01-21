import glob
import json
import os
from collections import defaultdict


OUT_DIR = r".\outputs"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_mode(filename: str) -> str:
    name = filename.lower()
    if "spacy" in name:
        return "spacy"
    if "zero" in name:
        return "gigachat_zero"
    if "few" in name:
        return "gigachat_few"
    return "unknown"


def main():
    files = glob.glob(os.path.join(OUT_DIR, "*_nel.json"))

    if not files:
        print("[WARN] No *_nel.json files found in outputs/")
        return

    stats = defaultdict(lambda: {"total": 0, "linked": 0})

    for path in files:
        mode = get_mode(os.path.basename(path))
        obj = load_json(path)

        for cell in obj.get("results", []):
            for ent in cell.get("entities", []):
                stats[mode]["total"] += 1
                if ent.get("kb_id"):
                    stats[mode]["linked"] += 1

    print("\nNEL statistics:\n")
    print(f"{'Model':15} | {'Total':>8} | {'Linked':>8} | {'Coverage %':>10}")
    print("-" * 50)

    for mode, s in stats.items():
        total = s["total"]
        linked = s["linked"]
        coverage = (linked / total * 100) if total else 0.0
        print(f"{mode:15} | {total:8} | {linked:8} | {coverage:9.2f}%")

    print("\nDone.")


if __name__ == "__main__":
    main()
