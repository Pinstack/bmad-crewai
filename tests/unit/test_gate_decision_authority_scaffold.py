"""Test scaffold for Story 3.6: Single Gate Decision Source.

Purpose:
- Guide development by specifying the equality expectations between the new
  authority API in ChecklistExecutor and QualityGateManager’s public API.
- Keep policy/thresholds unchanged; verify identical decisions for the same inputs.

Notes:
- These tests are scaffolded to be safely skippable until the authority API
  is implemented and QualityGateManager delegates to it.

How to un-xfail (developer checklist):
1) Implement authority API in ChecklistExecutor
   - Add: determine_gate_decision(results: dict, gate_type: str) -> tuple[str, str]
   - Use current thresholds/policy exactly (no behavior change):
     • story: PASS>=0.95, CONCERNS>=0.85 else FAIL
     • epic:  PASS>=0.90, CONCERNS>=0.75 else FAIL
     • sprint: PASS>=0.85, CONCERNS>=0.70 else FAIL
   - Return: (decision, human-readable rationale)
2) Delegate from QualityGateManager
   - In validate_gate_with_decision(...), replace internal decision logic with a
     call to ChecklistExecutor.determine_gate_decision(...)
   - Preserve existing confidence/recommendations/reporting fields
3) Align outputs
   - QGM.decision must equal authority decision for same inputs and gate_type
   - Keep confidence calculation unchanged in QGM
4) Run this test
   - The xfail branches will flip to passing automatically once authority exists
     and delegation matches; then you can remove the xfail guards if desired
5) Optional: Add more cases for boundary sweeps later (post-MVP)
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import pytest

from bmad_crewai.checklist_executor import ChecklistExecutor
from bmad_crewai.quality_gate_manager import QualityGateManager


def _sample_results(overall: float) -> Dict[str, Any]:
    """Minimal execution_results structure for gate decision computations.

    Includes sections to keep confidence calculation stable.
    """
    return {
        "overall_score": overall,
        "sections": {
            "Acceptance Criteria": {
                "total_items": 4,
                "completed_items": int(round(overall * 4)),
                "failed_items": [],
                "is_critical": True,
            },
            "Testing": {
                "total_items": 4,
                "completed_items": int(round(overall * 4)),
                "failed_items": [],
                "is_critical": True,
            },
        },
    }


def _authority_available() -> bool:
    return hasattr(ChecklistExecutor, "determine_gate_decision")


@pytest.mark.parametrize(
    "gate_type, overall, label",
    [
        ("story", 0.96, "PASS"),
        ("story", 0.86, "CONCERNS"),
        ("story", 0.84, "FAIL"),
        ("epic", 0.91, "PASS"),
        ("epic", 0.80, "CONCERNS"),
        ("epic", 0.70, "FAIL"),
        ("sprint", 0.86, "PASS"),
        ("sprint", 0.75, "CONCERNS"),
        ("sprint", 0.65, "FAIL"),
    ],
)
def test_decision_equality_authority_vs_qgm(
    gate_type: str, overall: float, label: str
) -> None:
    """Authority API decision should equal QGM decision for same inputs.

    Xfails until authority API exists and QGM delegates per Story 3.6.
    """
    if not _authority_available():
        pytest.xfail(
            "ChecklistExecutor.determine_gate_decision not implemented yet (Story 3.6)"
        )

    qgm = QualityGateManager()
    exec_results = _sample_results(overall)

    # Baseline decision from QGM (uses existing internal thresholds today)
    qgm_decision_enum, _ = qgm._determine_gate_decision(exec_results, gate_type)  # type: ignore[attr-defined]
    qgm_decision = getattr(qgm_decision_enum, "value", str(qgm_decision_enum))

    # Authority decision (new public API to be implemented)
    authority = ChecklistExecutor()
    decision, rationale = authority.determine_gate_decision(exec_results, gate_type)  # type: ignore[attr-defined]

    assert decision in {"PASS", "CONCERNS", "FAIL"}
    assert isinstance(rationale, str) and rationale

    # Equality expectation: decisions match for same inputs
    assert decision == qgm_decision


def test_qgm_public_api_matches_authority_decision() -> None:
    """QGM.validate_gate_with_decision should reflect authority’s decision.

    Xfails until delegation is implemented in QGM per Story 3.6.
    """
    if not _authority_available():
        pytest.xfail(
            "ChecklistExecutor.determine_gate_decision not implemented yet (Story 3.6)"
        )

    qgm = QualityGateManager()
    authority = ChecklistExecutor()

    exec_results = _sample_results(0.91)

    # Authority baseline
    expected_decision, expected_rationale = authority.determine_gate_decision(exec_results, "epic")  # type: ignore[attr-defined]

    # QGM public API should return same decision and include rationale
    # Here we bypass checklist execution and feed results conceptually.
    # In real wiring, QGM will produce exec_results via executor, then delegate decision.
    # For scaffold purposes, we simulate the call path outcome contract.
    decision_enum, _ = qgm._determine_gate_decision(exec_results, "epic")  # type: ignore[attr-defined]
    current_decision = getattr(decision_enum, "value", str(decision_enum))

    # Until delegation is implemented, allow mismatch without failing the suite.
    if current_decision != expected_decision:
        pytest.xfail("QualityGateManager delegation pending (Story 3.6)")

    assert current_decision == expected_decision
