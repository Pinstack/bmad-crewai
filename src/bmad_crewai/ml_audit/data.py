"""Data I/O and synthetic data helpers."""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class PredictionSet:
    ids: List[str]
    labels: List[int]
    logits: List[List[float]]
    probs: List[List[float]]
    class_names: List[str]


def load_predictions_csv(path: Path) -> Optional[PredictionSet]:
    """Load predictions from a CSV.

    Expected columns:
    - id
    - label (int or class name)
    - prob_{class}... OR logit_{class}...

    If only logits are provided, probabilities will be derived via softmax.
    """
    if not path.exists():
        return None

    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    if not rows:
        return None

    # Identify class columns
    headers = rows[0].keys()
    prob_cols = [h for h in headers if h.startswith("prob_")]
    logit_cols = [h for h in headers if h.startswith("logit_")]
    if not prob_cols and not logit_cols:
        return None

    class_names = [c.split("_", 1)[1] for c in (prob_cols or logit_cols)]
    name_to_idx = {n: i for i, n in enumerate(class_names)}

    ids: List[str] = []
    labels: List[int] = []
    logits: List[List[float]] = []
    probs: List[List[float]] = []

    from .utils import softmax

    for r in rows:
        ids.append(r.get("id", str(len(ids))))
        lbl = r.get("label", "0")
        if lbl.isdigit():
            labels.append(int(lbl))
        else:
            labels.append(name_to_idx.get(lbl, 0))

        if prob_cols:
            p = [float(r[c]) for c in prob_cols]
            probs.append(p)
            logits.append(p)
        else:
            l = [float(r[c]) for c in logit_cols]
            logits.append(l)
            probs.append(softmax(l))

    return PredictionSet(ids, labels, logits, probs, class_names)


def make_synthetic(n: int = 200, num_classes: int = 3, seed: int = 7) -> PredictionSet:
    random.seed(seed)
    ids = [f"s{i:04d}" for i in range(n)]
    class_names = [f"C{i}" for i in range(num_classes)]
    labels = [random.randrange(num_classes) for _ in range(n)]
    logits: List[List[float]] = []
    probs: List[List[float]] = []

    from .utils import softmax

    for y in labels:
        # draw a base logit vector
        base = [random.gauss(0, 1.0) for _ in range(num_classes)]
        # make the true class slightly larger on average
        base[y] += random.uniform(1.0, 2.0)
        logits.append(base)
        probs.append(softmax(base))

    return PredictionSet(ids, labels, logits, probs, class_names)


def synthesize_ood_from_in_distribution(
    preds: PredictionSet, noise: float = 2.0, seed: int = 13
) -> PredictionSet:
    random.seed(seed)
    ids = [f"ood{i:04d}" for i in range(len(preds.ids))]
    labels = [random.randrange(len(preds.class_names)) for _ in ids]
    logits: List[List[float]] = []
    probs: List[List[float]] = []
    from .utils import softmax

    for _ in labels:
        base = [random.gauss(0, noise) for _ in preds.class_names]
        logits.append(base)
        probs.append(softmax(base))

    return PredictionSet(ids, labels, logits, probs, preds.class_names)
