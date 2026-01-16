import os
import subprocess
import sys

TABLES_DIR = r".\data\all_tables"
OUT_DIR = r".\outputs"

os.makedirs(OUT_DIR, exist_ok=True)

MODES = ["zero", "few"]          # ← ОБА РЕЖИМА
TABLE_RANGE = range(207, 226)    # ← диапазон таблиц

for mode in MODES:
    print(f"\n===== GIGACHAT MODE: {mode.upper()} =====\n")

    for table_id in TABLE_RANGE:
        out_file = os.path.join(
            OUT_DIR,
            f"{table_id}_gigachat_{mode}.json"
        )

        print(f"=== Table {table_id} ({mode}) ===")

        cmd = [
            sys.executable,
            r".\src\run_gigachat.py",
            "--tables_dir", TABLES_DIR,
            "--table_id", str(table_id),
            "--out", out_file,
            "--mode", mode,
            "--drop_first_col", "auto",
            "--drop_header", "true",
            "--index_base", "1",
            "--quiet",
        ]

        res = subprocess.run(cmd)

        if res.returncode != 0:
            print(f"[WARN] Failed on table {table_id} ({mode}), exit={res.returncode}")
