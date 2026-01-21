# eval_ner.py
# Оценка качества NER: сопоставление pred ↔ test_set по table_id
# Авто-режим: оценивает 3 набора (spacy / gigachat_zero / gigachat_few) и сохраняет в reports/

import argparse
import json
import os
import glob
import re
from typing import Dict, Tuple, Set, Optional, Iterable


DEFAULT_PRED_DIR = r".\outputs"
DEFAULT_TEST_SET_DIR = r".\data\test_set"
DEFAULT_REPORTS_DIR = r".\reports"


def norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("\u00A0", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_table_id(filename: str) -> Optional[int]:
    base = os.path.basename(filename)
    m = re.search(r"(\d+)", base)
    return int(m.group(1)) if m else None


def parse_label_map(s: Optional[str]) -> Dict[str, str]:
    if not s:
        return {}
    out: Dict[str, str] = {}
    parts = [p.strip() for p in s.split(",") if p.strip()]
    for p in parts:
        if "=" not in p:
            raise ValueError(f"Неверный формат label_map: '{p}' (ожидается KEY=VALUE)")
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def parse_label_set(s: Optional[str]) -> Set[str]:
    if not s:
        return set()
    return {p.strip() for p in s.split(",") if p.strip()}


def apply_label_map(label: str, label_map: Dict[str, str]) -> str:
    return label_map.get(label, label)


def iter_entities(obj: dict) -> Iterable[Tuple[int, int, str, str]]:
    for cell in obj.get("results", []):
        row = cell.get("row")
        col = cell.get("col")
        for ent in (cell.get("entities") or []):
            text = ent.get("text")
            label = ent.get("label")
            if row is None or col is None or text is None or label is None:
                continue
            yield int(row), int(col), str(text), str(label)


def build_index(obj: dict, label_map: Dict[str, str], exclude_labels: Set[str]) -> Set[Tuple[int, int, str, str]]:
    out: Set[Tuple[int, int, str, str]] = set()
    for row, col, text, label in iter_entities(obj):
        label2 = apply_label_map(label, label_map)
        if label2 in exclude_labels:
            continue
        out.add((row, col, norm_text(text), label2))
    return out


def metrics(C: int, A: int, N: int) -> Tuple[float, float, float]:
    p = (C / A) if A else 0.0
    r = (C / N) if N else 0.0
    f1 = (2 * p * r / (p + r)) if (p + r) else 0.0
    return p, r, f1


def should_skip_pred_file(filename: str) -> bool:
    name = os.path.basename(filename).lower()
    return name.endswith("_nel.json") or "_nel" in name


def evaluate_one(
    pred_dir: str,
    test_set_dir: str,
    out_path: str,
    pred_glob: str,
    min_id: Optional[int],
    max_id: Optional[int],
    label_map: Dict[str, str],
    exclude_labels: Set[str],
    per_label: bool,
    strict_test_id: bool,
):
    pred_files = sorted(glob.glob(os.path.join(pred_dir, pred_glob)))
    pred_files = [p for p in pred_files if not should_skip_pred_file(p)]

    test_files = sorted(glob.glob(os.path.join(test_set_dir, "*.json")))

    if not test_files:
        print(f"[ERROR] Нет файлов test_set в {test_set_dir}")
        return

    test_by_id: Dict[int, str] = {}
    for f in test_files:
        tid = extract_table_id(f)
        if tid is None:
            continue
        if min_id is not None and tid < min_id:
            continue
        if max_id is not None and tid > max_id:
            continue
        if strict_test_id and tid in test_by_id:
            raise RuntimeError(f"В test_set несколько файлов с table_id={tid}: '{test_by_id[tid]}' и '{f}'")
        test_by_id[tid] = f

    total_C = 0
    total_A = 0
    total_N = 0
    total_FP = 0
    total_FN = 0

    skipped_out_of_range = 0
    skipped_no_test = 0

    per_table = []

    for pred_path in pred_files:
        tid = extract_table_id(pred_path)
        if tid is None:
            continue

        if min_id is not None and tid < min_id:
            skipped_out_of_range += 1
            continue
        if max_id is not None and tid > max_id:
            skipped_out_of_range += 1
            continue

        test_path = test_by_id.get(tid)
        if not test_path:
            skipped_no_test += 1
            continue

        pred_obj = load_json(pred_path)
        test_obj = load_json(test_path)

        pred_idx = build_index(pred_obj, label_map, exclude_labels)
        test_idx = build_index(test_obj, label_map, exclude_labels)

        correct = pred_idx & test_idx
        C = len(correct)
        A = len(pred_idx)
        N = len(test_idx)

        FP = A - C
        FN = N - C

        total_C += C
        total_A += A
        total_N += N
        total_FP += FP
        total_FN += FN

        p, r, f1 = metrics(C, A, N)

        row = {
            "table_id": tid,
            "pred_file": os.path.basename(pred_path),
            "test_file": os.path.basename(test_path),
            "C": C,
            "A": A,
            "N": N,
            "FP": FP,
            "FN": FN,
            "precision": p,
            "recall": r,
            "f1": f1,
        }

        if per_label:
            plc: Dict[str, Dict[str, int]] = {}
            for _, _, _, lb in test_idx:
                plc.setdefault(lb, {"C": 0, "A": 0, "N": 0})["N"] += 1
            for _, _, _, lb in pred_idx:
                plc.setdefault(lb, {"C": 0, "A": 0, "N": 0})["A"] += 1
            for _, _, _, lb in correct:
                plc.setdefault(lb, {"C": 0, "A": 0, "N": 0})["C"] += 1

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
            "pred_dir": os.path.abspath(pred_dir),
            "test_set_dir": os.path.abspath(test_set_dir),
            "min_id": min_id,
            "max_id": max_id,
            "label_map": label_map,
            "exclude_labels": sorted(exclude_labels),
            "per_label": per_label,
            "pred_glob": pred_glob,
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
        },
    }

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[OK] Таблиц оценено: {len(per_table)}")
    if min_id is not None or max_id is not None:
        print(f"[OK] Диапазон: {min_id}..{max_id}")
    if exclude_labels:
        print(f"[OK] Исключённые метки: {', '.join(sorted(exclude_labels))}")
    if label_map:
        print(f"[OK] label_map: {', '.join([f'{k}->{v}' for k, v in label_map.items()])}")
    print(f"[OK] Overall F1 = {f1:.4f}")
    print(f"[OK] Отчёт сохранён: {out_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Оценка качества NER по test_set (spacy / zero / few)")

    parser.add_argument("--pred_dir", default=DEFAULT_PRED_DIR, help="Папка с предсказаниями (JSON)")
    parser.add_argument("--test_set_dir", default=DEFAULT_TEST_SET_DIR, help="Папка с test_set (JSON)")
    parser.add_argument("--reports_dir", default=DEFAULT_REPORTS_DIR, help="Куда сохранять отчёты")

    parser.add_argument("--min_id", type=int, default=None, help="Минимальный table_id (включительно)")
    parser.add_argument("--max_id", type=int, default=None, help="Максимальный table_id (включительно)")
    parser.add_argument("--label_map", default=None, help='Маппинг меток, например: "GPE=LOC,PER=PERSON"')
    parser.add_argument("--exclude_labels", default=None, help='Исключить метки, например: "QUANTITY,DATE"')
    parser.add_argument("--per_label", action="store_true", help="Добавить метрики по каждой метке")
    parser.add_argument(
        "--strict_test_id",
        action="store_true",
        help="Если у test_set несколько файлов на один table_id — считать это ошибкой",
    )

    args = parser.parse_args()

    label_map = parse_label_map(args.label_map)
    exclude_labels = parse_label_set(args.exclude_labels)

    os.makedirs(args.reports_dir, exist_ok=True)

    evaluate_one(
        pred_dir=args.pred_dir,
        test_set_dir=args.test_set_dir,
        out_path=os.path.join(args.reports_dir, "ner_report_spacy.json"),
        pred_glob="*_spacy.json",
        min_id=args.min_id,
        max_id=args.max_id,
        label_map=label_map,
        exclude_labels=exclude_labels,
        per_label=args.per_label,
        strict_test_id=args.strict_test_id,
    )

    evaluate_one(
        pred_dir=args.pred_dir,
        test_set_dir=args.test_set_dir,
        out_path=os.path.join(args.reports_dir, "ner_report_gigachat_zero.json"),
        pred_glob="*_gigachat_zero.json",
        min_id=args.min_id,
        max_id=args.max_id,
        label_map=label_map,
        exclude_labels=exclude_labels,
        per_label=args.per_label,
        strict_test_id=args.strict_test_id,
    )

    evaluate_one(
        pred_dir=args.pred_dir,
        test_set_dir=args.test_set_dir,
        out_path=os.path.join(args.reports_dir, "ner_report_gigachat_few.json"),
        pred_glob="*_gigachat_few.json",
        min_id=args.min_id,
        max_id=args.max_id,
        label_map=label_map,
        exclude_labels=exclude_labels,
        per_label=args.per_label,
        strict_test_id=args.strict_test_id,
    )


if __name__ == "__main__":
    main()
