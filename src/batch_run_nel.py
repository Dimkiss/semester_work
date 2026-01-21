import argparse
import glob
import os
import subprocess


def build_out_path(in_path: str, in_dir: str, out_dir: str, suffix: str) -> str:
    rel = os.path.relpath(in_path, in_dir)
    base, ext = os.path.splitext(rel)
    out_rel = f"{base}{suffix}{ext}"
    return os.path.join(out_dir, out_rel)


def main():
    p = argparse.ArgumentParser(description="Batch NEL: прогнать run_nel.py по множеству NER-json")
    p.add_argument("--in_dir", required=True, help="Папка с NER-json (вход)")
    p.add_argument("--out_dir", required=True, help="Папка для NEL-json (выход)")
    p.add_argument("--pattern", default="*.json", help="Паттерн файлов (например spacy_*.json)")
    p.add_argument("--suffix", default="_nel", help="Суффикс к имени выходного файла")
    p.add_argument("--limit", type=int, default=5, help="limit для wbsearchentities")
    p.add_argument("--sleep", type=float, default=0.05, help="Пауза между запросами (сек)")
    p.add_argument("--timeout", type=float, default=10.0, help="Timeout http (сек)")
    p.add_argument("--skip-existing", action="store_true", help="Пропускать, если выходной файл уже есть")

    args = p.parse_args()

    in_glob = os.path.join(args.in_dir, "**", args.pattern)
    files = sorted(glob.glob(in_glob, recursive=True))

    if not files:
        print(f"[WARN] No files: {in_glob}")
        return

    os.makedirs(args.out_dir, exist_ok=True)

    ok = 0
    skipped = 0
    failed = 0

    for in_path in files:
        out_path = build_out_path(in_path, args.in_dir, args.out_dir, args.suffix)

        if args.skip_existing and os.path.exists(out_path):
            skipped += 1
            continue

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        cmd = [
            "python",
            "run_nel.py",
            "--in_ner", in_path,
            "--out", out_path,
            "--limit", str(args.limit),
            "--sleep", str(args.sleep),
            "--timeout", str(args.timeout),
            "--quiet",
        ]

        try:
            subprocess.run(cmd, check=True)
            ok += 1
        except subprocess.CalledProcessError:
            failed += 1

    print(f"[OK] done: {ok}, skipped: {skipped}, failed: {failed}")


if __name__ == "__main__":
    main()
