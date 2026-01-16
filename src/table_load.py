# table_load.py
import csv
import os
import re
from typing import List, Dict, Optional, Tuple

NUMBER_CELL_RE = re.compile(r"^\d+(\.\d+)?$")


class RF200TableLoader:
    def __init__(self, tables_dir: str, verbose: bool = True):
        self.tables_dir = tables_dir
        self.verbose = verbose

    def _find_table_file(self, table_id: int) -> Optional[str]:
        for filename in os.listdir(self.tables_dir):
            if filename.startswith(f"{table_id}_") and filename.endswith(".csv"):
                return os.path.join(self.tables_dir, filename)
        return None

    def _probe_delimiter(self, path: str, delimiters: List[str], probe_lines: int = 20) -> str:
        """
        Выбирает delimiter по максимуму "полезного разбиения":
        берём тот, где среднее число колонок на первых probe_lines строках максимальное.
        """
        best_delim = delimiters[0]
        best_score = -1.0

        for d in delimiters:
            with open(path, encoding="utf-8", newline="") as f:
                reader = csv.reader(f, delimiter=d)
                rows = []
                for _, row in zip(range(probe_lines), reader):
                    rows.append(row)

            if not rows:
                continue

            lens = [len(r) for r in rows if r]
            score = (sum(lens) / len(lens)) if lens else 0.0

            if score > best_score:
                best_score = score
                best_delim = d

        return best_delim

    def _read_csv_auto(self, path: str) -> Tuple[str, List[List[str]]]:
        candidates = ["|", "\t", ";", ","]  # у тебя реально '|' как разделитель колонок
        delim = self._probe_delimiter(path, candidates)

        with open(path, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f, delimiter=delim))

        if self.verbose:
            # приблизительная оценка колонок
            nonempty = [r for r in rows[:20] if r]
            avg_cols = (sum(len(r) for r in nonempty) / len(nonempty)) if nonempty else 0.0
            print(f"[INFO] delimiter auto = {repr(delim)}, avg_cols≈{avg_cols:.1f}")

        return delim, rows

    def _auto_detect_drop_first_col(self, data_rows: List[List[str]]) -> bool:
        """
        True если >=80% непустых значений в первом столбце — числа вида 1 или 1.0
        """
        values = []
        for row in data_rows:
            if not row:
                continue
            v = row[0].strip()
            if v:
                values.append(v)

        if not values:
            return False

        numeric_count = sum(1 for v in values if NUMBER_CELL_RE.match(v))
        return (numeric_count / len(values)) >= 0.8

    def load_table(
        self,
        table_id: int,
        drop_first_col: Optional[bool] = None,  # None = auto
        drop_header: bool = True
    ) -> List[Dict]:
        path = self._find_table_file(table_id)

        if path is None:
            if self.verbose:
                print(f"[WARN] Таблица {table_id} отсутствует — пропуск")
            return []

        if self.verbose:
            print(f"[OK] Файл таблицы: {path}")

        delim, rows = self._read_csv_auto(path)
        if not rows:
            return []

        # 1) убираем заголовок
        data_rows = rows[1:] if drop_header else rows

        # 2) решаем, удалять ли первый столбец
        if drop_first_col is None:
            drop_first_col = self._auto_detect_drop_first_col(data_rows)
            if self.verbose:
                print(f"[INFO] auto drop_first_col = {drop_first_col}")
        else:
            if self.verbose:
                print(f"[INFO] drop_first_col = {drop_first_col} (forced)")

        # 3) формируем плоский список ячеек
        cells: List[Dict] = []
        start_row_idx = 1 if drop_header else 0

        for r_i, row in enumerate(data_rows, start=start_row_idx):
            if not row:
                continue

            cols = row[1:] if drop_first_col else row
            col_shift = 1 if drop_first_col else 0

            for c_i, cell in enumerate(cols):
                cell_str = "" if cell is None else str(cell).strip()
                if not cell_str:
                    continue

                # ВАЖНО:
                # - если delimiter='|', то '|' — это разделитель СТОЛБЦОВ,
                #   и внутри ячейки делить по '|' нельзя.
                # - иначе можно поддержать "мультизначения" в ячейке через '|'
                if delim == "|":
                    parts = [cell_str]
                else:
                    parts = [p.strip() for p in cell_str.split("|") if p.strip()]

                for text in parts:
                    cells.append({
                        "table_id": table_id,
                        "row": r_i,
                        "col": c_i + col_shift,
                        "text": text
                    })

        return cells
