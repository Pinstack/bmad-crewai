"""Entrypoint for running ML audit artefact generation.

Usage (from repo root):
  PYTHONPATH=src python -m bmad_crewai.ml_audit.run --outdir reports \
      [--predictions data/predictions.csv]

If no predictions are provided, a small synthetic dataset is used so that
artefacts are still generated. This does not change any model behaviour.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

from .data import (
    PredictionSet,
    load_predictions_csv,
    make_synthetic,
    synthesize_ood_from_in_distribution,
)
from .metrics import (
    compute_basic_metrics,
    energy_scores,
    find_temperature_for_ece,
    msp_scores,
    ood_auroc_aupr,
    threshold_for_tpr,
)
from .plots import (
    confusion_matrix_png,
    montage_3x3_placeholder,
    ood_roc_png,
    pr_curves_png,
    reliability_png,
    uncertainty_hist_png,
)
from .utils import argmax, pr_points


def _write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write("")
        return
    cols = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _write_markdown_table(metrics: Dict[str, object]) -> str:
    # Single, compact metrics table per requirements
    cm = metrics["confusion_matrix"]
    per_f1 = metrics["f1"]
    acc = metrics["accuracy"]
    macro_f1 = metrics["macro_f1"]
    ece = metrics["ece"]
    # OOD placeholders added later by runner
    return (
        "| Metric | Value |\n"
        "|---|---|\n"
        f"| Accuracy | {acc:.3f} |\n"
        f"| Macro-F1 | {macro_f1:.3f} |\n"
        f"| Per-class F1 | {', '.join(f'{x:.3f}' for x in per_f1)} |\n"
        f"| ECE | {ece:.3f} |\n"
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Run ML audit and generate artefacts")
    p.add_argument("--predictions", type=str, default="", help="CSV with predictions")
    p.add_argument("--outdir", type=str, default="reports", help="Output directory")
    p.add_argument("--synthetic", action="store_true", help="Force synthetic data")
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    pred_path = Path(args.predictions) if args.predictions else None
    pred: Optional[PredictionSet] = None
    if pred_path:
        pred = load_predictions_csv(pred_path)
    if pred is None:
        pred = make_synthetic()

    metrics = compute_basic_metrics(pred.labels, pred.probs)

    # Errors FP/FN top-K (use K=20 or all if fewer)
    preds = metrics["preds"]
    top1_conf = metrics["top1_conf"]
    rows_fp: List[Dict[str, object]] = []
    rows_fn: List[Dict[str, object]] = []
    for i, (y, a, c) in enumerate(zip(pred.labels, preds, top1_conf)):
        row = {"id": pred.ids[i], "true": y, "pred": a, "conf": round(float(c), 6)}
        if a != y:
            rows_fn.append(row)
            rows_fp.append(row)
    rows_fp = sorted(rows_fp, key=lambda r: -float(r["conf"]))[:20]
    rows_fn = sorted(rows_fn, key=lambda r: -float(r["conf"]))[:20]
    _write_csv(outdir / "errors_fp.csv", rows_fp)
    _write_csv(outdir / "errors_fn.csv", rows_fn)

    # Ambiguity
    ambiguous_idx = metrics["ambiguous_idx"]
    amb_rows = [
        {
            "id": pred.ids[i],
            "true": pred.labels[i],
            "pred": preds[i],
            "margin": round(float(metrics["margins"][i]), 6),
            "entropy": round(float(metrics["entropies"][i]), 6),
        }
        for i in ambiguous_idx
    ]
    _write_csv(outdir / "ambiguous.csv", amb_rows)

    # Plots
    confusion_matrix_png(
        metrics["confusion_matrix"], outdir / "confusion_matrix.png", pred.class_names
    )
    # PR curves per class: build one-vs-rest PR using class probabilities
    pr_curves = []
    for k in range(metrics["num_classes"]):
        labels_bin = [1 if y == k else 0 for y in pred.labels]
        scores = [row[k] for row in pred.probs]
        pr_curves.append(pr_points(scores, labels_bin))
    pr_curves_png(pr_curves, outdir / "pr_curves.png")
    reliability_png(
        metrics["top1_conf"], metrics["correct"], outdir / "calibration_reliability.png"
    )
    uncertainty_hist_png(metrics["margins"], outdir / "uncertainty_hist.png")
    montage_3x3_placeholder(outdir / "errors_montage.png")

    # OOD using synthetic OOD if none provided
    ood = synthesize_ood_from_in_distribution(pred)
    msp_in = msp_scores(pred.probs)
    msp_ood = msp_scores(ood.probs)
    energy_in = energy_scores(pred.logits)
    energy_ood = energy_scores(ood.logits)
    auroc_msp, aupr_msp = ood_auroc_aupr(msp_in, msp_ood, higher_is_in=True)
    auroc_energy, aupr_energy = ood_auroc_aupr(
        energy_in, energy_ood, higher_is_in=False
    )
    # Mahalanobis not available (no embeddings) -> N/A
    ood_roc_png(None, None, outdir / "ood_roc.png")

    # Thresholds (example: MSP threshold for 95% TPR to accept in-distribution)
    labels_in_vs_ood = [1] * len(msp_in) + [0] * len(msp_ood)
    th_msp = threshold_for_tpr(
        msp_in + msp_ood, labels_in_vs_ood, 0.95, higher_is_positive=True
    )
    th_energy = threshold_for_tpr(
        energy_in + energy_ood, labels_in_vs_ood, 0.95, higher_is_positive=False
    )

    # Temperature scaling (report-only)
    T_best, ece_post = find_temperature_for_ece(pred.logits, pred.labels)

    # Write ML audit report
    md = ["# ML Audit\n"]
    md.append("## Executive Summary\n")
    md.append(
        "This repository does not include a conventional ML model; the audit pipeline ran on provided predictions if available, otherwise on a small synthetic dataset to validate the auditing process. Thresholds and OOD results are illustrative unless real predictions are supplied.\n"
    )
    md.append("## Metrics\n")
    md.append(_write_markdown_table(metrics))
    md.append("\n")
    md.append("### OOD (MSP/Energy)\n")
    md.append(f"- AUROC MSP: {auroc_msp:.3f}, AUPR MSP: {aupr_msp:.3f}\n")
    md.append(f"- AUROC Energy: {auroc_energy:.3f}, AUPR Energy: {aupr_energy:.3f}\n")
    md.append("\n")
    md.append("### Calibration\n")
    md.append(
        f"- Temperature scaling best T: {T_best:.2f}, post-calibration ECE: {ece_post:.3f} (not applied by default)\n"
    )
    md.append("\n")
    md.append("## Threshold Recommendations\n")
    md.append("- Ambiguity flag: margin ≤ 0.10 or entropy ≥ 0.5·log(C)\n")
    md.append(
        f"- OOD reject (MSP): threshold ≈ {th_msp if th_msp is not None else 'N/A'} (accept if score ≥ th)\n"
    )
    md.append(
        f"- OOD reject (Energy): threshold ≈ {th_energy if th_energy is not None else 'N/A'} (accept if score ≤ th)\n"
    )
    md.append(
        "- Confidence gating: require top-1 ≥ 0.8 for auto-accept; route ambiguous to human/QA.\n"
    )
    md.append("\n")
    md.append("## Artefacts\n")
    md.append("- confusion_matrix.png, pr_curves.png, calibration_reliability.png\n")
    md.append(
        "- ood_roc.png, uncertainty_hist.png, errors_fp.csv, errors_fn.csv, ambiguous.csv\n"
    )

    (outdir / "ml_audit.md").write_text("".join(md), encoding="utf-8")


if __name__ == "__main__":
    main()
