import glob
import os
import subprocess
import sys

OUT_DIR = r".\outputs"
PATTERN = "*.json"


def is_nel_file(path: str) -> bool:
    name = os.path.basename(path).lower()
    return name.endswith("_nel.json") or "_nel" in name


def out_path_for(in_path: str) -> str:
    base = os.path.basename(in_path)
    name, ext = os.path.splitext(base)
    return os.path.join(OUT_DIR, f"{name}_nel{ext}")


def main():
    files = sorted(glob.glob(os.path.join(OUT_DIR, PATTERN)))

    if not files:
        print(f"[WARN] No files found in {OUT_DIR} by pattern {PATTERN}")
        return

    ok = 0
    skipped = 0
    failed = 0

    for in_path in files:
        if is_nel_file(in_path):
            skipped += 1
            continue

        out_path = out_path_for(in_path)

        cmd = [
            sys.executable,
            r".\src\run_nel.py",
            "--in_ner", in_path,
            "--out", out_path,
            "--quiet",
        ]

        res = subprocess.run(cmd)
        if res.returncode == 0:
            ok += 1
        else:
            failed += 1
            print(f"[WARN] Failed: {in_path} (exit={res.returncode})")

    print(f"[OK] done: {ok}, skipped: {skipped}, failed: {failed}")
    print(f"[OK] outputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
