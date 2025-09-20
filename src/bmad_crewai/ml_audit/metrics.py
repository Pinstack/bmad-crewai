"""Core metrics for ML audit.

All implementations are dependency-light and operate on Python lists.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from .utils import (
    ap_from_pr,
    argmax,
    auc_roc,
    ece,
    entropy,
    mce,
    pr_points,
    softmax,
    top1_margin,
)


def confusion_matrix(
    labels: Sequence[int], preds: Sequence[int], num_classes: int
) -> List[List[int]]:
    cm = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
    for y, p in zip(labels, preds):
        if 0 <= y < num_classes and 0 <= p < num_classes:
            cm[y][p] += 1
    return cm


def precision_recall_f1(
    cm: List[List[int]],
) -> Tuple[List[float], List[float], List[float]]:
    k = len(cm)
    prec, rec, f1 = [], [], []
    for c in range(k):
        tp = cm[c][c]
        fp = sum(cm[r][c] for r in range(k)) - tp
        fn = sum(cm[c][r] for r in range(k)) - tp
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
        prec.append(p)
        rec.append(r)
        f1.append(f)
    return prec, rec, f1


def accuracy(cm: List[List[int]]) -> float:
    total = sum(sum(r) for r in cm)
    correct = sum(cm[i][i] for i in range(len(cm)))
    return correct / total if total > 0 else 0.0


def macro_f1(f1_per_class: Sequence[float]) -> float:
    return sum(f1_per_class) / len(f1_per_class) if f1_per_class else 0.0


def compute_basic_metrics(
    labels: Sequence[int],
    probs: Sequence[Sequence[float]],
) -> Dict[str, object]:
    num_classes = len(probs[0]) if probs else 0
    preds = [argmax(p) for p in probs]
    cm = confusion_matrix(labels, preds, num_classes)
    prec, rec, f1 = precision_recall_f1(cm)
    acc = accuracy(cm)
    macro = macro_f1(f1)

    top1 = [max(p) if p else 0.0 for p in probs]
    correct = [1 if y == a else 0 for y, a in zip(labels, preds)]
    ece_val = ece(top1, correct)
    mce_val = mce(top1, correct)

    margins = [top1_margin(p) for p in probs]
    entropies = [entropy(p) for p in probs]

    # Ambiguity per spec
    import math as _m

    H_thresh = 0.5 * _m.log(max(num_classes, 2)) if num_classes else 0.0
    ambiguous = [
        i
        for i, (m, h) in enumerate(zip(margins, entropies))
        if m <= 0.1 or h >= H_thresh
    ]

    return {
        "num_classes": num_classes,
        "confusion_matrix": cm,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "accuracy": acc,
        "macro_f1": macro,
        "ece": ece_val,
        "mce": mce_val,
        "ambiguous_idx": ambiguous,
        "margins": margins,
        "entropies": entropies,
        "preds": preds,
        "top1_conf": top1,
        "correct": correct,
    }


def msp_scores(probs: Sequence[Sequence[float]]) -> List[float]:
    return [max(p) if p else 0.0 for p in probs]


def energy_scores(logits: Sequence[Sequence[float]]) -> List[float]:
    # -T * logsumexp(logits/T) with T=1; we can just compute logsumexp and negate
    out: List[float] = []
    for ls in logits:
        if not ls:
            out.append(0.0)
            continue
        m = max(ls)
        s = sum(math.exp(x - m) for x in ls)
        lse = m + math.log(s)
        out.append(-lse)
    return out


def ood_auroc_aupr(
    in_scores: Sequence[float], ood_scores: Sequence[float], higher_is_in: bool = True
) -> Tuple[float, float]:
    # Build binary labels: 1=in-distribution, 0=OOD
    scores = list(in_scores) + list(ood_scores)
    labels = [1] * len(in_scores) + [0] * len(ood_scores)
    if not higher_is_in:
        scores = [-s for s in scores]
    auroc = auc_roc(scores, labels)
    # Use PR with positive=in
    pr = pr_points(scores, labels)
    aupr = ap_from_pr(pr)
    return auroc, aupr


def threshold_for_tpr(
    scores: Sequence[float],
    labels: Sequence[int],
    target_tpr: float = 0.95,
    higher_is_positive: bool = True,
) -> Optional[float]:
    pairs = sorted(
        zip(scores, labels), key=lambda x: x[0], reverse=not higher_is_positive
    )
    pos = sum(labels)
    if pos == 0:
        return None
    tp = 0
    best_th: Optional[float] = None
    for s, y in pairs:
        if y == 1:
            tp += 1
        tpr = tp / pos
        best_th = s
        if tpr >= target_tpr:
            return best_th
    return best_th


def temperature_scale(logits: Sequence[Sequence[float]], T: float) -> List[List[float]]:
    def scale_row(row: Sequence[float]) -> List[float]:
        return [x / max(T, 1e-6) for x in row]

    return [scale_row(r) for r in logits]


def find_temperature_for_ece(
    logits: Sequence[Sequence[float]],
    labels: Sequence[int],
    grid: Sequence[float] = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 5.0),
) -> Tuple[float, float]:
    """Grid search temperature that minimizes ECE; returns (T, ECE).
    Does not change any model behavior by default; use only for reporting."""
    best_T = 1.0
    best_e = float("inf")
    for T in grid:
        scaled = temperature_scale(logits, T)
        probs = [softmax(r) for r in scaled]
        top1 = [max(p) if p else 0.0 for p in probs]
        preds = [argmax(p) for p in probs]
        correct = [1 if y == a else 0 for y, a in zip(labels, preds)]
        e = ece(top1, correct)
        if e < best_e:
            best_e = e
            best_T = T
    return best_T, best_e
