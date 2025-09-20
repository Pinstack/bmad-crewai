"""Integration tests for the gate decision authority delegation flow.

Tests the complete integration between QualityGateManager and ChecklistExecutor
to ensure the authority API works correctly end-to-end.
"""

from unittest.mock import Mock, patch

import pytest

from src.bmad_crewai.quality_gate_manager import QualityGateManager


class TestGateDelegationIntegration:
    """Test suite for complete gate decision delegation flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = QualityGateManager()

    def test_story_gate_delegation_end_to_end(self):
        """Test complete delegation flow for story gate."""
        # Mock the checklist executor to return controlled results
        with patch.object(self.manager, "checklist_executor") as mock_executor:
            # Mock checklist execution results
            mock_executor.execute_checklist.return_value = {
                "overall_score": 0.97,
                "sections": {
                    "Acceptance Criteria": {
                        "total_items": 3,
                        "completed_items": 3,
                        "failed_items": [],
                        "is_critical": True,
                    },
                    "Testing": {
                        "total_items": 2,
                        "completed_items": 2,
                        "failed_items": [],
                        "is_critical": True,
                    },
                },
                "artefact_type": "story",
            }

            # Mock the authority API response
            mock_executor.determine_gate_decision.return_value = (
                "PASS",
                "Story meets all quality criteria with excellent completion",
            )

            # Execute the full flow
            result = self.manager.validate_gate_with_decision(
                "story-dod-checklist", "story"
            )

            # Verify the delegation worked correctly
            assert result["decision"] == "PASS"
            assert (
                result["decision_rationale"]
                == "Story meets all quality criteria with excellent completion"
            )
            assert result["gate_type"] == "story"
            assert result["confidence_score"] >= 0.9

            # Verify the authority API was called with correct parameters
            mock_executor.determine_gate_decision.assert_called_once_with(
                mock_executor.execute_checklist.return_value, "story"
            )

    def test_epic_gate_delegation_end_to_end(self):
        """Test complete delegation flow for epic gate."""
        with patch.object(self.manager, "checklist_executor") as mock_executor:
            mock_executor.execute_checklist.return_value = {
                "overall_score": 0.88,
                "sections": {
                    "Story List": {
                        "total_items": 5,
                        "completed_items": 4,
                        "failed_items": ["Missing story 3"],
                        "is_critical": False,
                    },
                },
                "artefact_type": "epic",
            }

            mock_executor.determine_gate_decision.return_value = (
                "CONCERNS",
                "Epic has acceptable quality but some areas need attention",
            )

            result = self.manager.validate_gate_with_decision("epic-checklist", "epic")

            assert result["decision"] == "CONCERNS"
            assert "acceptable quality" in result["decision_rationale"]
            assert result["gate_type"] == "epic"

    def test_sprint_gate_delegation_end_to_end(self):
        """Test complete delegation flow for sprint gate."""
        with patch.object(self.manager, "checklist_executor") as mock_executor:
            mock_executor.execute_checklist.return_value = {
                "overall_score": 0.82,
                "sections": {
                    "Sprint Goals": {
                        "total_items": 3,
                        "completed_items": 3,
                        "failed_items": [],
                        "is_critical": True,
                    },
                },
                "artefact_type": "sprint",
            }

            mock_executor.determine_gate_decision.return_value = (
                "CONCERNS",
                "Sprint acceptable but team should address quality issues",
            )

            result = self.manager.validate_gate_with_decision(
                "sprint-checklist", "sprint"
            )

            assert result["decision"] == "CONCERNS"
            assert "acceptable but" in result["decision_rationale"]
            assert result["gate_type"] == "sprint"

    def test_release_gate_delegation_end_to_end(self):
        """Test complete delegation flow for release gate."""
        with patch.object(self.manager, "checklist_executor") as mock_executor:
            mock_executor.execute_checklist.return_value = {
                "overall_score": 0.96,
                "sections": {
                    "Release Criteria": {
                        "total_items": 10,
                        "completed_items": 10,
                        "failed_items": [],
                        "is_critical": True,
                    },
                },
                "artefact_type": "release",
            }

            mock_executor.determine_gate_decision.return_value = (
                "PASS",
                "Release meets all quality requirements for production deployment",
            )

            result = self.manager.validate_gate_with_decision(
                "release-checklist", "release"
            )

            assert result["decision"] == "PASS"
            assert "production deployment" in result["decision_rationale"]
            assert result["gate_type"] == "release"

    def test_fail_gate_delegation_end_to_end(self):
        """Test complete delegation flow for failing gate."""
        with patch.object(self.manager, "checklist_executor") as mock_executor:
            mock_executor.execute_checklist.return_value = {
                "overall_score": 0.6,
                "sections": {
                    "Critical Requirements": {
                        "total_items": 5,
                        "completed_items": 2,
                        "failed_items": ["Req 3", "Req 4", "Req 5"],
                        "is_critical": True,
                    },
                },
                "artefact_type": "story",
            }

            mock_executor.determine_gate_decision.return_value = (
                "FAIL",
                "Story does not meet minimum quality standards",
            )

            result = self.manager.validate_gate_with_decision(
                "story-dod-checklist", "story"
            )

            assert result["decision"] == "FAIL"
            assert "minimum quality standards" in result["decision_rationale"]
            assert result["gate_type"] == "story"
            assert result["confidence_score"] < 0.7

    def test_error_handling_in_delegation_flow(self):
        """Test error handling in the delegation flow."""
        with patch.object(self.manager, "checklist_executor") as mock_executor:
            # Mock checklist execution failure
            mock_executor.execute_checklist.return_value = {
                "error": "Checklist execution failed"
            }

            result = self.manager.validate_gate_with_decision(
                "invalid-checklist", "story"
            )

            assert "error" in result
            assert result["error"] == "Checklist execution failed"

            # Authority API should not be called when execution fails
            mock_executor.determine_gate_decision.assert_not_called()

    def test_authority_api_exception_handling(self):
        """Test exception handling when authority API fails."""
        with patch.object(self.manager, "checklist_executor") as mock_executor:
            mock_executor.execute_checklist.return_value = {
                "overall_score": 0.9,
                "sections": {},
                "artefact_type": "story",
            }

            # Mock authority API to raise exception
            mock_executor.determine_gate_decision.side_effect = Exception(
                "Authority API error"
            )

            result = self.manager.validate_gate_with_decision(
                "story-dod-checklist", "story"
            )

            assert "error" in result
            assert "Authority API error" in result["error"]

    def test_delegation_preserves_backward_compatibility(self):
        """Test that delegation preserves all existing QGM behavior."""
        with patch.object(self.manager, "checklist_executor") as mock_executor:
            mock_executor.execute_checklist.return_value = {
                "overall_score": 0.95,
                "sections": {
                    "Acceptance Criteria": {
                        "total_items": 3,
                        "completed_items": 3,
                        "failed_items": [],
                        "is_critical": True,
                    },
                },
                "artefact_type": "story",
            }

            mock_executor.determine_gate_decision.return_value = (
                "PASS",
                "Story meets all quality criteria with excellent completion",
            )

            # Test new enhanced API
            result = self.manager.validate_gate_with_decision(
                "story-dod-checklist", "story"
            )

            # Verify all expected fields are present (backward compatibility)
            required_fields = [
                "gate_type",
                "checklist_id",
                "decision",
                "decision_rationale",
                "execution_results",
                "confidence_score",
                "critical_issues",
                "recommendations",
                "artefact_types_validated",
            ]

            for field in required_fields:
                assert field in result, f"Missing required field: {field}"

            assert result["decision"] == "PASS"
            assert isinstance(result["confidence_score"], (int, float))
            assert isinstance(result["critical_issues"], list)
            assert isinstance(result["recommendations"], list)
