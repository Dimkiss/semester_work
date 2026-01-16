import os
import subprocess
import sys

TABLES_DIR = r".\data\all_tables"
OUT_DIR = r".\outputs"

os.makedirs(OUT_DIR, exist_ok=True)

for table_id in range(201, 226):
    out_file = os.path.join(OUT_DIR, f"{table_id}_spacy.json")
    print(f"=== Table {table_id} ===")

    cmd = [
        sys.executable, r".\src\run.py",
        "--tables_dir", TABLES_DIR,
        "--table_id", str(table_id),
        "--out", out_file,
        "--drop_first_col", "auto",
        "--drop_header", "true",
        "--index_base", "1",   # ← ВАЖНО
        "--quiet",
    ]


    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"[WARN] Failed on table {table_id} (exit={res.returncode})")
