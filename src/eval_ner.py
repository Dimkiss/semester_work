# eval_ner.py
# Оценка качества NER: сопоставление pred ↔ test_set по table_id
# Улучшения:
# 1) extract_table_id понимает: "201_*.json", "201*.json", "table201*.json" (берёт первый блок цифр)
# 2) Фильтр по диапазону table_id: --min_id / --max_id (например 201..213)
# 3) Опциональный маппинг меток (например GPE->LOC): --label_map "GPE=LOC,PER=PERSON"
# 4) Можно исключать метки из оценки: --exclude_labels "QUANTITY,DATE"
# 5) Доп. статистика: FP/FN и (опционально) метрики по каждой метке: --per_label
#
# :contentReference[oaicite:0]{index=0}

import argparse
import json
import os
import glob
import re
from typing import Dict, Tuple, Set, Optional, Iterable


def norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("\u00A0", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_table_id(filename: str) -> Optional[int]:
    """
    Извлекает table_id из имени файла.
    Поддерживает:
      - 201_spacy.json -> 201
      - 201_locations_table.json -> 201
      - 201.json -> 201
      - table201_pred.json -> 201
    Берём первый блок цифр в имени файла.
    """
    base = os.path.basename(filename)
    m = re.search(r"(\d+)", base)
    return int(m.group(1)) if m else None


def parse_label_map(s: Optional[str]) -> Dict[str, str]:
    """
    "GPE=LOC,PER=PERSON" -> {"GPE": "LOC", "PER": "PERSON"}
    """
    if not s:
        return {}
    out: Dict[str, str] = {}
    parts = [p.strip() for p in s.split(",") if p.strip()]
    for p in parts:
        if "=" not in p:
            raise ValueError(f"Неверный формат --label_map: {p} (ожидается A=B)")
        a, b = [x.strip() for x in p.split("=", 1)]
        if not a or not b:
            raise ValueError(f"Неверный формат --label_map: {p} (пустая сторона)")
        out[a] = b
    return out


def parse_label_set(s: Optional[str]) -> Set[str]:
    """
    "QUANTITY,DATE" -> {"QUANTITY","DATE"}
    """
    if not s:
        return set()
    return {p.strip() for p in s.split(",") if p.strip()}


def apply_label_map(label: Optional[str], label_map: Dict[str, str]) -> Optional[str]:
    if label is None:
        return None
    return label_map.get(label, label)


def index_entities(
    table_obj: dict,
    label_map: Dict[str, str],
    exclude_labels: Set[str],
) -> Dict[Tuple[int, int], Set[Tuple[str, str]]]:
    """
    Индекс: (row,col) -> set((norm_text(entity_text), label))
    """
    idx: Dict[Tuple[int, int], Set[Tuple[str, str]]] = {}

    for cell in table_obj.get("results", []):
        try:
            key = (int(cell["row"]), int(cell["col"]))
        except Exception:
            # если формат внезапно кривой — пропускаем клетку
            continue

        idx.setdefault(key, set())

        for e in cell.get("entities", []):
            et = norm_text(e.get("text", ""))
            lb = apply_label_map(e.get("label"), label_map)
            if not et or not lb:
                continue
            if lb in exclude_labels:
                continue
            idx[key].add((et, lb))

    return idx


def compute_counts(
    pred_idx: Dict[Tuple[int, int], Set[Tuple[str, str]]],
    test_idx: Dict[Tuple[int, int], Set[Tuple[str, str]]],
) -> Tuple[int, int, int, int, int]:
    """
    Возвращает:
      C = correct (пересечение)
      A = predicted all
      N = gold all
      FP = false positives
      FN = false negatives
    """
    C = A = N = FP = FN = 0
    all_cells = set(pred_idx) | set(test_idx)

    for cell in all_cells:
        p = pred_idx.get(cell, set())
        t = test_idx.get(cell, set())
        inter = p & t
        C += len(inter)
        A += len(p)
        N += len(t)
        FP += len(p - t)
        FN += len(t - p)

    return C, A, N, FP, FN


def metrics(C: int, A: int, N: int) -> Tuple[float, float, float]:
    precision = C / A if A else 0.0
    recall = C / N if N else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def per_label_counts(
    pred_idx: Dict[Tuple[int, int], Set[Tuple[str, str]]],
    test_idx: Dict[Tuple[int, int], Set[Tuple[str, str]]],
) -> Dict[str, Dict[str, int]]:
    """
    Для каждой метки считает C/A/N (строгий match по (text,label)).
    """
    out: Dict[str, Dict[str, int]] = {}
    all_cells = set(pred_idx) | set(test_idx)

    for cell in all_cells:
        p = pred_idx.get(cell, set())
        t = test_idx.get(cell, set())

        labels = {lb for _, lb in p} | {lb for _, lb in t}
        for lb in labels:
            out.setdefault(lb, {"C": 0, "A": 0, "N": 0})
            p_lb = {(et, l) for (et, l) in p if l == lb}
            t_lb = {(et, l) for (et, l) in t if l == lb}
            out[lb]["C"] += len(p_lb & t_lb)
            out[lb]["A"] += len(p_lb)
            out[lb]["N"] += len(t_lb)

    return out


def in_range(tid: int, min_id: Optional[int], max_id: Optional[int]) -> bool:
    if min_id is not None and tid < min_id:
        return False
    if max_id is not None and tid > max_id:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Оценка качества NER по test_set (сопоставление по table_id)"
    )
    parser.add_argument("--pred_dir", required=True, help="Папка с предсказаниями (JSON)")
    parser.add_argument("--test_set_dir", required=True, help="Папка с test_set (JSON)")
    parser.add_argument("--out", required=True, help="JSON-отчёт")

    # новые опции
    parser.add_argument("--min_id", type=int, default=None, help="Минимальный table_id (включительно)")
    parser.add_argument("--max_id", type=int, default=None, help="Максимальный table_id (включительно)")
    parser.add_argument(
        "--label_map",
        default=None,
        help='Маппинг меток, например: "GPE=LOC,PER=PERSON"'
    )
    parser.add_argument(
        "--exclude_labels",
        default=None,
        help='Исключить метки из оценки, например: "QUANTITY,DATE"'
    )
    parser.add_argument(
        "--per_label",
        action="store_true",
        help="Добавить в отчёт метрики по каждой метке"
    )
    parser.add_argument(
        "--strict_test_id",
        action="store_true",
        help="Если у test_set несколько файлов на один table_id — считать это ошибкой (иначе берём последний найденный)"
    )

    args = parser.parse_args()

    try:
        label_map = parse_label_map(args.label_map)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return

    exclude_labels = parse_label_set(args.exclude_labels)

    pred_files = glob.glob(os.path.join(args.pred_dir, "*.json"))
    test_files = glob.glob(os.path.join(args.test_set_dir, "*.json"))

    if not pred_files:
        print("[ERROR] Нет файлов предсказаний")
        return
    if not test_files:
        print("[ERROR] Нет файлов test_set")
        return

    # индексируем test_set по tid
    test_map: Dict[int, str] = {}
    collisions: Dict[int, Set[str]] = {}

    for tf in test_files:
        tid = extract_table_id(os.path.basename(tf))
        if tid is None:
            continue
        if not in_range(tid, args.min_id, args.max_id):
            continue

        if tid in test_map:
            collisions.setdefault(tid, set()).update({test_map[tid], tf})
        test_map[tid] = tf  # по умолчанию берём последний

    if args.strict_test_id and collisions:
        print("[ERROR] В test_set найдено несколько файлов для одного table_id:")
        for tid, files in sorted(collisions.items()):
            print(f"  table_id={tid}:")
            for f in sorted(files):
                print(f"    - {os.path.basename(f)}")
        print("Переименуйте файлы или отключите --strict_test_id.")
        return

    total_C = total_A = total_N = total_FP = total_FN = 0
    per_table = []
    skipped_no_test = 0
    skipped_out_of_range = 0

    # сортировка для красивого отчёта
    pred_files_sorted = sorted(pred_files, key=lambda p: (extract_table_id(os.path.basename(p)) or 10**12, p))

    for pf in pred_files_sorted:
        fname = os.path.basename(pf)
        tid = extract_table_id(fname)

        if tid is None:
            continue

        if not in_range(tid, args.min_id, args.max_id):
            skipped_out_of_range += 1
            continue

        if tid not in test_map:
            print(f"[WARN] Нет test_set для {fname} (table_id={tid})")
            skipped_no_test += 1
            continue

        pred = load_json(pf)
        test = load_json(test_map[tid])

        pred_idx = index_entities(pred, label_map=label_map, exclude_labels=exclude_labels)
        test_idx = index_entities(test, label_map=label_map, exclude_labels=exclude_labels)

        C, A, N, FP, FN = compute_counts(pred_idx, test_idx)
        p, r, f1 = metrics(C, A, N)

        total_C += C
        total_A += A
        total_N += N
        total_FP += FP
        total_FN += FN

        row = {
            "table_id": tid,
            "pred_file": fname,
            "test_file": os.path.basename(test_map[tid]),
            "method": pred.get("method"),
            "C": C,
            "A": A,
            "N": N,
            "FP": FP,
            "FN": FN,
            "precision": p,
            "recall": r,
            "f1": f1,
        }

        if args.per_label:
            plc = per_label_counts(pred_idx, test_idx)
            per_label_report = {}
            for lb, cnts in plc.items():
                lp, lr, lf1 = metrics(cnts["C"], cnts["A"], cnts["N"])
                per_label_report[lb] = {
                    "C": cnts["C"],
                    "A": cnts["A"],
                    "N": cnts["N"],
                    "precision": lp,
                    "recall": lr,
                    "f1": lf1,
                }
            row["per_label"] = per_label_report

        per_table.append(row)

    p, r, f1 = metrics(total_C, total_A, total_N)

    report = {
        "config": {
            "pred_dir": os.path.abspath(args.pred_dir),
            "test_set_dir": os.path.abspath(args.test_set_dir),
            "min_id": args.min_id,
            "max_id": args.max_id,
            "label_map": label_map,
            "exclude_labels": sorted(exclude_labels),
            "per_label": args.per_label,
        },
        "per_table": per_table,
        "overall": {
            "C": total_C,
            "A": total_A,
            "N": total_N,
            "FP": total_FP,
            "FN": total_FN,
            "precision": p,
            "recall": r,
            "f1": f1,
        },
        "skipped": {
            "pred_out_of_range": skipped_out_of_range,
            "pred_without_test": skipped_no_test,
        }
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[OK] Таблиц оценено: {len(per_table)}")
    if args.min_id is not None or args.max_id is not None:
        print(f"[OK] Диапазон: {args.min_id}..{args.max_id}")
    if exclude_labels:
        print(f"[OK] Исключённые метки: {', '.join(sorted(exclude_labels))}")
    if label_map:
        print(f"[OK] label_map: {', '.join([f'{k}->{v}' for k,v in label_map.items()])}")
    print(f"[OK] Overall F1 = {f1:.4f}")
    print(f"[OK] Отчёт сохранён: {args.out}")


if __name__ == "__main__":
    main()
