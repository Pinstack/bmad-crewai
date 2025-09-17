# Gate Matrix

| Artefact | Gate | Checklists | Owner | Pass Criteria | Waiver | Severity Caps |
|----------|------|------------|-------|---------------|--------|---------------|
| PRD | GATE_PO_VALID | CHK_PO_MASTER, CHK_PM | PO | All BLOCKER=PASS; MAJOR≤1; MINOR any | Yes | No waiver on BLOCKER |
| Architecture | GATE_ARCH | CHK_ARCH, CHK_NFR | Architect | BLOCKER=PASS; MAJOR=0; MINOR≤3 | Limited | No waiver on security BLOCKER |
| Story | GATE_DOD | CHK_DOD | Dev | All mandatory items PASS | No | — |
| Story | GATE_QA | CHK_QA_GATE | QA | All critical issues fixed; risk ≤ Medium | Waive "CONCERNS" only | Critical unwaivable |
| Release | GATE_RELEASE | CHK_SEC, CHK_NFR | QA/Sec | No regressions vs baselines | No | — |
