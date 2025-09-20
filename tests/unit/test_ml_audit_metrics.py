"""Unit tests for ML audit metrics utilities."""

from __future__ import annotations

from bmad_crewai.ml_audit.metrics import confusion_matrix, macro_f1, precision_recall_f1
from bmad_crewai.ml_audit.utils import ece, mce


def test_confusion_and_f1_simple():
    labels = [0, 0, 1, 1]
    preds = [0, 1, 1, 1]
    cm = confusion_matrix(labels, preds, 2)
    assert cm == [[1, 1], [0, 2]]
    p, r, f1 = precision_recall_f1(cm)
    # class 0: tp=1, fp=0, fn=1 -> p=1.0, r=0.5, f1=0.667
    assert abs(p[0] - 1.0) < 1e-6
    assert abs(r[0] - 0.5) < 1e-6
    assert abs(f1[0] - (2 * 1.0 * 0.5 / (1.5))) < 1e-6
    # class 1: tp=2, fp=1, fn=0 -> p=0.667, r=1.0
    assert abs(r[1] - 1.0) < 1e-6
    assert 0.66 < p[1] < 0.67
    assert 0.79 < macro_f1(f1) < 0.80


def test_calibration_errors():
    confs = [0.9, 0.8, 0.6, 0.4, 0.2]
    correct = [1, 1, 0, 0, 0]
    e = ece(confs, correct, n_bins=5)
    m = mce(confs, correct, n_bins=5)
    assert 0.0 <= e <= 1.0
    assert 0.0 <= m <= 1.0
