# ML Audit
## Executive Summary
This repository does not include a conventional ML model; the audit pipeline ran on provided predictions if available, otherwise on a small synthetic dataset to validate the auditing process. Thresholds and OOD results are illustrative unless real predictions are supplied.
## Metrics
| Metric | Value |
|---|---|
| Accuracy | 0.755 |
| Macro-F1 | 0.753 |
| Per-class F1 | 0.752, 0.795, 0.713 |
| ECE | 0.089 |

### OOD (MSP/Energy)
- AUROC MSP: 0.402, AUPR MSP: 0.423
- AUROC Energy: 0.554, AUPR Energy: 0.485

### Calibration
- Temperature scaling best T: 0.75, post-calibration ECE: 0.058 (not applied by default)

## Threshold Recommendations
- Ambiguity flag: margin ≤ 0.10 or entropy ≥ 0.5·log(C)
- OOD reject (MSP): threshold ≈ 0.9193784156190724 (accept if score ≥ th)
- OOD reject (Energy): threshold ≈ -3.3094325951628267 (accept if score ≤ th)
- Confidence gating: require top-1 ≥ 0.8 for auto-accept; route ambiguous to human/QA.

## Artefacts
- confusion_matrix.png, pr_curves.png, calibration_reliability.png
- ood_roc.png, uncertainty_hist.png, errors_fp.csv, errors_fn.csv, ambiguous.csv
