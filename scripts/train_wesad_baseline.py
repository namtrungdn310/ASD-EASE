"""Huấn luyện và đánh giá mô hình Baseline nhận diện Stress trên WESAD.

Quy trình:
- Phân chia Leave-One-Subject-Out (LOSO) trên toàn bộ 15 đối tượng (không rò rỉ dữ liệu giữa các người).
- Fit scaler (StandardScaler) CHỈ trên tập train của từng fold, không fit trên test subject.
- Thử nghiệm cắt bỏ đặc trưng (Ablation Study):
  1. EDA only (14 features)
  2. ACC only (13 features)
  3. EDA + ACC (27 features - hoàn toàn không phụ thuộc HR)
  4. Full Multimodal (EDA + ACC + HR + hr_is_valid - 36 features)
- Báo cáo Accuracy, Macro F1, Stress F1, Non-stress F1 theo từng người và tổng hợp toàn bộ.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
from src.preprocessing.wesad import write_csv, write_json
from audit_wesad import SUBJECTS


def load_dataset(dataset_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    with dataset_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    fieldnames = reader.fieldnames or []
    meta_cols = {"subject_id", "window_start_ms", "window_end_ms", "source_label_code", "label"}
    feat_cols = [c for c in fieldnames if c not in meta_cols]

    subjects = np.array([r["subject_id"] for r in rows])
    labels = np.array([int(r["label"]) for r in rows], dtype=int)
    X = np.array([[float(r[c]) for c in feat_cols] for r in rows], dtype=float)

    return X, labels, subjects, feat_cols


def run_loso_cross_validation(
    X: np.ndarray,
    y: np.ndarray,
    subjects: np.ndarray,
    model_fn,
    selected_indices: list[int] | None = None,
) -> dict:
    unique_subjects = np.unique(subjects)
    all_y_true = []
    all_y_pred = []
    per_subject_metrics = {}

    for test_subj in unique_subjects:
        test_mask = subjects == test_subj
        train_mask = ~test_mask

        X_train, y_train = X[train_mask], y[train_mask]
        X_test, y_test = X[test_mask], y[test_mask]

        if selected_indices is not None:
            X_train = X_train[:, selected_indices]
            X_test = X_test[:, selected_indices]

        # Chuẩn hoá scaler chỉ fit trên train
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Huấn luyện mô hình
        clf = model_fn()
        clf.fit(X_train_scaled, y_train)

        # Dự đoán
        preds = clf.predict(X_test_scaled)
        all_y_true.extend(y_test)
        all_y_pred.extend(preds)

        acc = float(accuracy_score(y_test, preds))
        f1_macro = float(f1_score(y_test, preds, average="macro", zero_division=0))
        f1_stress = float(f1_score(y_test, preds, pos_label=1, zero_division=0))
        f1_non_stress = float(f1_score(y_test, preds, pos_label=0, zero_division=0))

        per_subject_metrics[test_subj] = {
            "test_windows": int(len(y_test)),
            "accuracy": acc,
            "f1_macro": f1_macro,
            "f1_stress": f1_stress,
            "f1_non_stress": f1_non_stress,
        }

    all_y_true = np.array(all_y_true)
    all_y_pred = np.array(all_y_pred)

    overall_acc = float(accuracy_score(all_y_true, all_y_pred))
    overall_f1_macro = float(f1_score(all_y_true, all_y_pred, average="macro", zero_division=0))
    overall_f1_stress = float(f1_score(all_y_true, all_y_pred, pos_label=1, zero_division=0))
    overall_f1_non_stress = float(f1_score(all_y_true, all_y_pred, pos_label=0, zero_division=0))
    overall_prec_stress = float(precision_score(all_y_true, all_y_pred, pos_label=1, zero_division=0))
    overall_rec_stress = float(recall_score(all_y_true, all_y_pred, pos_label=1, zero_division=0))
    cm = confusion_matrix(all_y_true, all_y_pred).tolist()

    return {
        "overall": {
            "accuracy": overall_acc,
            "f1_macro": overall_f1_macro,
            "f1_stress": overall_f1_stress,
            "f1_non_stress": overall_f1_non_stress,
            "precision_stress": overall_prec_stress,
            "recall_stress": overall_rec_stress,
            "confusion_matrix": cm,
        },
        "macro_subject": {
            "mean_accuracy": float(np.mean([m["accuracy"] for m in per_subject_metrics.values()])),
            "mean_f1_macro": float(np.mean([m["f1_macro"] for m in per_subject_metrics.values()])),
            "mean_f1_stress": float(np.mean([m["f1_stress"] for m in per_subject_metrics.values()])),
            "mean_f1_non_stress": float(np.mean([m["f1_non_stress"] for m in per_subject_metrics.values()])),
        },
        "per_subject": per_subject_metrics,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "ai/data/processed/wesad/features-v1/dataset.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "ai/models/wesad-baseline-v1",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        parser.error(f"Dataset not found at {args.dataset}. Run extract_wesad_features.py first.")

    if args.output.exists():
        parser.error(f"Output directory {args.output} already exists; choose a new path.")

    args.output.mkdir(parents=True)
    started = datetime.now(timezone(timedelta(hours=7))).isoformat()

    print("Loading dataset...", flush=True)
    X, y, subjects, feature_names = load_dataset(args.dataset)
    print(f"Loaded {len(X)} windows across {len(np.unique(subjects))} subjects, {len(feature_names)} features.")

    # Phân nhóm đặc trưng
    eda_indices = [i for i, f in enumerate(feature_names) if f.startswith("eda_")]
    acc_indices = [i for i, f in enumerate(feature_names) if f.startswith("acc_")]
    hr_indices = [i for i, f in enumerate(feature_names) if f.startswith("hr_")]
    eda_acc_indices = eda_indices + acc_indices
    all_indices = list(range(len(feature_names)))

    modality_experiments = {
        "EDA_only": eda_indices,
        "ACC_only": acc_indices,
        "EDA_and_ACC": eda_acc_indices,
        "Full_Multimodal": all_indices,
    }

    report = {
        "version": "wesad-baseline-loso-v1",
        "started_at": started,
        "status": "RUNNING",
        "total_windows": len(X),
        "total_subjects": len(np.unique(subjects)),
        "models": {},
    }

    print("\n--- Running Leave-One-Subject-Out (LOSO) Cross Validation with Random Forest ---")
    rf_factory = lambda: RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight="balanced")

    for mod_name, idx_list in modality_experiments.items():
        print(f"Evaluating {mod_name} ({len(idx_list)} features)...", flush=True)
        res = run_loso_cross_validation(X, y, subjects, rf_factory, selected_indices=idx_list)
        ov = res["overall"]
        mac = res["macro_subject"]
        print(
            f"  -> Acc: {100*ov['accuracy']:.2f}%, F1 Macro: {100*ov['f1_macro']:.2f}%, Stress F1: {100*ov['f1_stress']:.2f}%, Stress Recall: {100*ov['recall_stress']:.2f}%"
        )
        report["models"][f"RandomForest_{mod_name}"] = res

    print("\n--- Running Linear Baseline (Logistic Regression) on Full Multimodal ---")
    lr_factory = lambda: LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    lr_res = run_loso_cross_validation(X, y, subjects, lr_factory, selected_indices=all_indices)
    ov = lr_res["overall"]
    print(f"  -> Acc: {100*ov['accuracy']:.2f}%, F1 Macro: {100*ov['f1_macro']:.2f}%, Stress F1: {100*ov['f1_stress']:.2f}%")
    report["models"]["LogisticRegression_Full_Multimodal"] = lr_res

    print("\n--- Running HistGradientBoosting on Full Multimodal ---")
    hgb_factory = lambda: HistGradientBoostingClassifier(random_state=42, class_weight="balanced")
    hgb_res = run_loso_cross_validation(X, y, subjects, hgb_factory, selected_indices=all_indices)
    ov = hgb_res["overall"]
    print(f"  -> Acc: {100*ov['accuracy']:.2f}%, F1 Macro: {100*ov['f1_macro']:.2f}%, Stress F1: {100*ov['f1_stress']:.2f}%")
    report["models"]["HistGradientBoosting_Full_Multimodal"] = hgb_res

    report["status"] = "COMPLETE"
    report["completed_at"] = datetime.now(timezone(timedelta(hours=7))).isoformat()
    write_json(args.output / "report.json", report)
    print(f"\nAll experiments complete! Results saved to: {args.output}")


if __name__ == "__main__":
    main()
