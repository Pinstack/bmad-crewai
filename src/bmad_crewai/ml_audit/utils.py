"""Small, pure-Python helpers for metrics computations."""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple


def softmax(logits: Sequence[float]) -> List[float]:
    if not logits:
        return []
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    s = sum(exps)
    return [e / s for e in exps]


def entropy(prob: Sequence[float], eps: float = 1e-12) -> float:
    return -sum(p * math.log(max(p, eps)) for p in prob)


def top1_margin(prob: Sequence[float]) -> float:
    if not prob:
        return 0.0
    s = sorted(prob, reverse=True)
    if len(s) == 1:
        return s[0]
    return s[0] - s[1]


def argmax(xs: Sequence[float]) -> int:
    mi, mv = 0, float("-inf")
    for i, v in enumerate(xs):
        if v > mv:
            mi, mv = i, v
    return mi


def auc_roc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Compute AUROC for binary labels (1=positive) using rank statistic.

    Pure-Python variant: O(n log n)."""
    pairs = sorted(zip(scores, labels), key=lambda x: x[0], reverse=True)
    pos = sum(labels)
    neg = len(labels) - pos
    if pos == 0 or neg == 0:
        return float("nan")

    tp = 0
    fp = 0
    prev_score = None
    tpr_fpr: List[Tuple[float, float]] = [(0.0, 0.0)]

    # Count positives/negatives encountered as threshold sweeps
    p_seen = 0
    n_seen = 0
    for score, y in pairs:
        if prev_score is None or score != prev_score:
            # Record point
            if prev_score is not None:
                tpr = p_seen / pos
                fpr = n_seen / neg
                tpr_fpr.append((fpr, tpr))
            prev_score = score
        if y == 1:
            p_seen += 1
        else:
            n_seen += 1

    tpr = p_seen / pos
    fpr = n_seen / neg
    tpr_fpr.append((fpr, tpr))

    # Sort by FPR and trapezoidal integrate TPR over FPR
    tpr_fpr.sort(key=lambda x: x[0])
    area = 0.0
    for (x0, y0), (x1, y1) in zip(tpr_fpr[:-1], tpr_fpr[1:]):
        area += (x1 - x0) * (y0 + y1) / 2.0
    return area


def pr_points(
    scores: Sequence[float], labels: Sequence[int]
) -> List[Tuple[float, float]]:
    """Precision-Recall curve points for binary labels (1=positive)."""
    pairs = sorted(zip(scores, labels), key=lambda x: x[0], reverse=True)
    tp = 0
    fp = 0
    fn = sum(labels)
    points: List[Tuple[float, float]] = []
    prev_score = None
    for score, y in pairs:
        if prev_score is None or score != prev_score:
            if tp + fp > 0:
                precision = tp / (tp + fp)
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                points.append((recall, precision))
            prev_score = score
        if y == 1:
            tp += 1
            fn -= 1
        else:
            fp += 1
    if tp + fp > 0:
        precision = tp / (tp + fp)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        points.append((recall, precision))
    return points


def ap_from_pr(points: Sequence[Tuple[float, float]]) -> float:
    if not points:
        return float("nan")
    # Sort by recall ascending
    pts = sorted(points)
    area = 0.0
    for (r0, p0), (r1, p1) in zip(pts[:-1], pts[1:]):
        # Step-wise interpolation (approx)
        area += (r1 - r0) * max(p0, p1)
    return area


def ece(prob_true: Sequence[float], labels: Sequence[int], n_bins: int = 15) -> float:
    """Expected Calibration Error for binary correctness vs confidence.

    prob_true: model confidence for the predicted class (top-1 probability).
    labels: 1 if prediction correct, else 0.
    """
    if not prob_true:
        return 0.0
    bins = [i / n_bins for i in range(n_bins + 1)]
    total = len(prob_true)
    e = 0.0
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        idx = [
            j for j, p in enumerate(prob_true) if (p > lo if i else p >= lo) and p <= hi
        ]
        if not idx:
            continue
        conf = sum(prob_true[j] for j in idx) / len(idx)
        acc = sum(labels[j] for j in idx) / len(idx)
        e += (len(idx) / total) * abs(acc - conf)
    return e


def mce(prob_true: Sequence[float], labels: Sequence[int], n_bins: int = 15) -> float:
    if not prob_true:
        return 0.0
    bins = [i / n_bins for i in range(n_bins + 1)]
    gaps: List[float] = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        idx = [
            j for j, p in enumerate(prob_true) if (p > lo if i else p >= lo) and p <= hi
        ]
        if not idx:
            continue
        conf = sum(prob_true[j] for j in idx) / len(idx)
        acc = sum(labels[j] for j in idx) / len(idx)
        gaps.append(abs(acc - conf))
    return max(gaps) if gaps else 0.0
