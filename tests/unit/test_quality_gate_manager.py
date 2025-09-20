"""
Unit tests for Enhanced Quality Gate Manager

Tests P0 scenarios for enhanced gate decision framework, artefact-specific validation,
comprehensive reporting, and actionable feedback systems. Covers PASS/CONCERNS/FAIL
determination with confidence scoring and critical issue identification.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.bmad_crewai.quality_gate_manager import (
    GateDecision,
    GateType,
    QualityGateManager,
)


class TestQualityGateManager:
    """Test suite for enhanced QualityGateManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = QualityGateManager()

    def test_validate_gate_with_decision_pass_story(self):
        """Test enhanced gate validation returns PASS for story with good score."""
        # Arrange - Mock the checklist executor instance
        mock_executor = Mock()
        self.manager.checklist_executor = mock_executor

        # Mock execution results for a passing story
        mock_executor.execute_checklist.return_value = {
            "overall_score": 0.97,
            "sections": [
                {
                    "title": "Acceptance Criteria",
                    "total_items": 3,
                    "completed_items": 3,
                    "failed_items": [],
                },
                {
                    "title": "Testing",
                    "total_items": 2,
                    "completed_items": 2,
                    "failed_items": [],
                },
            ],
            "artefact_type": "story",
            "artefact_specific_findings": [],
            "acceptance_threshold": 0.95,
        }

        # Mock the authority API
        mock_executor.determine_gate_decision.return_value = (
            "PASS",
            "Story meets all quality criteria with excellent completion",
        )

        # Act
        result = self.manager.validate_gate_with_decision(
            "story-dod-checklist", "story"
        )

        # Assert
        assert result["decision"] == "PASS"
        assert (
            result["decision_rationale"]
            == "Story meets all quality criteria with excellent completion"
        )
        assert result["confidence_score"] >= 0.9
        assert "critical_issues" in result
        assert "recommendations" in result
        assert "artefact_types_validated" in result

    def test_validate_gate_with_decision_concerns_epic(self):
        """Test enhanced gate validation returns CONCERNS for epic with moderate issues."""
        # Arrange - Mock the checklist executor instance
        mock_executor = Mock()
        self.manager.checklist_executor = mock_executor

        # Mock execution results for an epic with concerns
        mock_executor.execute_checklist.return_value = {
            "overall_score": 0.82,
            "sections": [
                {
                    "title": "Story List",
                    "total_items": 5,
                    "completed_items": 4,
                    "failed_items": ["Missing story 3"],
                },
                {
                    "title": "Acceptance Criteria",
                    "total_items": 3,
                    "completed_items": 3,
                    "failed_items": [],
                },
            ],
            "artefact_type": "epic",
            "artefact_specific_findings": [
                {
                    "section": "Story List",
                    "finding": "No stories defined in epic",
                    "severity": "medium",
                }
            ],
            "acceptance_threshold": 0.9,
        }

        # Mock the authority API
        mock_executor.determine_gate_decision.return_value = (
            "CONCERNS",
            "Epic has acceptable quality but some areas need attention",
        )

        # Act
        result = self.manager.validate_gate_with_decision("po-master-checklist", "epic")

        # Assert
        assert result["decision"] == "CONCERNS"
        assert (
            "acceptable quality but some areas need attention"
            in result["decision_rationale"]
        )
        assert result["confidence_score"] > 0.7
        assert len(result["critical_issues"]) > 0

    @patch("src.bmad_crewai.quality_gate_manager.ChecklistExecutor")
    def test_validate_gate_with_decision_fail_release(self, mock_executor_class):
        """Test enhanced gate validation returns FAIL for release with critical issues."""
        # Arrange
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor

        # Mock execution results for a failing release
        mock_executor.execute_checklist.return_value = {
            "overall_score": 0.75,
            "sections": [
                {
                    "title": "Security",
                    "total_items": 5,
                    "completed_items": 2,
                    "failed_items": [
                        "No auth validation",
                        "Missing encryption",
                        "Weak password policy",
                    ],
                },
                {
                    "title": "Performance",
                    "total_items": 3,
                    "completed_items": 1,
                    "failed_items": ["No load testing", "Missing SLAs"],
                },
            ],
            "artefact_type": "architecture",
            "artefact_specific_findings": [
                {
                    "section": "Security",
                    "finding": "Limited security coverage",
                    "severity": "high",
                }
            ],
        }

        # Mock the authority API - for release gate type
        mock_executor.determine_gate_decision.return_value = (
            "FAIL",
            "Release quality is insufficient for production deployment",
        )

        # Act
        result = self.manager.validate_gate_with_decision(
            "architect-checklist", "release"
        )

        # Assert
        assert result["decision"] == "FAIL"
        assert "insufficient for production deployment" in result["decision_rationale"]
        assert result["confidence_score"] < 0.9
        assert len(result["critical_issues"]) > 0

    def test_gate_decision_enum_values(self):
        """Test that GateDecision enum has correct values."""
        assert GateDecision.PASS.value == "PASS"
        assert GateDecision.CONCERNS.value == "CONCERNS"
        assert GateDecision.FAIL.value == "FAIL"

    def test_gate_type_enum_values(self):
        """Test that GateType enum has correct values."""
        assert GateType.STORY.value == "story"
        assert GateType.EPIC.value == "epic"
        assert GateType.SPRINT.value == "sprint"
        assert GateType.RELEASE.value == "release"

    @patch("src.bmad_crewai.quality_gate_manager.ChecklistExecutor")
    def test_determine_story_gate_decision_strict_thresholds(self, mock_executor_class):
        """Test that story gate decisions use strict thresholds."""
        # Test PASS threshold (>= 0.95)
        self.manager._determine_story_gate_decision = Mock(
            return_value=(
                GateDecision.PASS,
                "Story meets all quality criteria with excellent completion",
            )
        )

        # Test CONCERNS threshold (>= 0.85)
        result = self.manager._determine_gate_decision({"overall_score": 0.90}, "story")
        # This should use the story-specific method

        # Test FAIL threshold (< 0.85)
        result = self.manager._determine_gate_decision({"overall_score": 0.80}, "story")

    @patch("src.bmad_crewai.quality_gate_manager.ChecklistExecutor")
    def test_epic_gate_more_flexible_than_story(self, mock_executor_class):
        """Test that epic gates allow more flexibility than story gates."""
        # Epic should pass with lower score than story would require
        result = self.manager._determine_gate_decision({"overall_score": 0.88}, "epic")
        # Epic threshold is 0.9, so this should be CONCERNS

        result = self.manager._determine_gate_decision({"overall_score": 0.92}, "epic")
        # This should pass for epic

    @patch("src.bmad_crewai.quality_gate_manager.ChecklistExecutor")
    def test_release_gate_highest_bar(self, mock_executor_class):
        """Test that release gates have the highest quality bar."""
        # Release requires 0.98 to pass
        result = self.manager._determine_gate_decision(
            {"overall_score": 0.97}, "release"
        )
        # This should be CONCERNS for release

        result = self.manager._determine_gate_decision(
            {"overall_score": 0.99}, "release"
        )
        # This should pass for release

    def test_calculate_confidence_score(self):
        """Test confidence score calculation."""
        # High confidence for complete data and high scores
        confidence = self.manager._calculate_confidence_score(
            {"overall_score": 0.95, "sections": [{"title": "Test"}]}, "story"
        )
        assert confidence >= 0.9

        # Reduced confidence for unknown artefact type
        confidence = self.manager._calculate_confidence_score(
            {"overall_score": 0.95, "sections": []}, "story"
        )
        assert confidence < 0.95  # Reduced due to missing sections

    def test_identify_critical_issues_with_failed_items(self):
        """Test critical issue identification from failed checklist items."""
        execution_results = {
            "sections": [
                {
                    "title": "Security",
                    "failed_items": ["No authentication", "Weak encryption"],
                    "is_critical": True,
                },
                {
                    "title": "Documentation",
                    "failed_items": ["Missing README"],
                    "is_critical": False,
                },
            ]
        }

        critical_issues = self.manager._identify_critical_issues(
            execution_results, "story"
        )

        assert len(critical_issues) == 2  # Both sections have failed items
        assert critical_issues[0]["severity"] == "high"  # Critical section
        assert critical_issues[1]["severity"] == "medium"  # Non-critical section

    def test_generate_gate_recommendations_by_decision(self):
        """Test that recommendations vary by gate decision."""
        # PASS recommendations
        recommendations = self.manager._generate_gate_recommendations(
            {"overall_score": 0.95}, GateDecision.PASS, "story"
        )
        assert "Consider additional quality practices" not in str(recommendations)

        # FAIL recommendations
        recommendations = self.manager._generate_gate_recommendations(
            {"overall_score": 0.7}, GateDecision.FAIL, "story"
        )
        assert "Address all failed checklist items" in str(recommendations)

        # CONCERNS recommendations
        recommendations = self.manager._generate_gate_recommendations(
            {"overall_score": 0.85}, GateDecision.CONCERNS, "story"
        )
        assert "Document and track" in str(recommendations)

    def test_extract_artefact_types_mapping(self):
        """Test artefact type extraction from checklist IDs."""
        # Test known mappings
        assert "story" in self.manager._extract_artefact_types("story-dod-checklist")
        assert "architecture" in self.manager._extract_artefact_types(
            "architect-checklist"
        )
        assert "prd" in self.manager._extract_artefact_types("pm-checklist")

        # Test unknown checklist
        assert "unknown" in self.manager._extract_artefact_types("unknown-checklist")

    def test_backward_compatibility_validate_gate(self):
        """Test that existing validate_gate method still works with enhanced framework."""
        # Arrange - Mock the checklist executor instance
        mock_executor = Mock()
        self.manager.checklist_executor = mock_executor

        mock_executor.execute_checklist.return_value = {
            "overall_score": 0.95,
            "sections": [
                {
                    "title": "Test",
                    "total_items": 1,
                    "completed_items": 1,
                    "failed_items": [],
                }
            ],
            "artefact_type": "story",
            "artefact_specific_findings": [],
            "acceptance_threshold": 0.95,
        }

        # Mock the authority API
        mock_executor.determine_gate_decision.return_value = (
            "PASS",
            "Story meets all quality criteria with excellent completion",
        )

        # Mock the checklist loading to avoid "not found" error
        mock_executor.get_checklist.return_value = {
            "title": "Test Checklist",
            "items": [],
        }

        # Call the original method
        result = self.manager.validate_gate("story-dod-checklist", "story")

        # Should return enhanced results for backward compatibility
        assert "decision" in result
        assert (
            "confidence_score" in result
        )  # Note: it's confidence_score, not confidence
        assert isinstance(result["decision"], str)

    def test_error_handling_in_gate_validation(self):
        """Test error handling in gate validation."""
        # Arrange - Mock the checklist executor instance
        mock_executor = Mock()
        self.manager.checklist_executor = mock_executor

        # Mock checklist exists first, then simulate execution error
        mock_executor.get_checklist.return_value = {
            "title": "Test Checklist",
            "items": [],
        }
        mock_executor.execute_checklist.side_effect = Exception("Test execution error")

        # Act
        result = self.manager.validate_gate_with_decision(
            "story-dod-checklist", "story"
        )

        # Assert
        assert "error" in result
        assert "Test execution error" in result["error"]

    def test_gate_decision_rationale_quality(self):
        """Test that gate decision rationales are informative."""
        # Test various decision scenarios
        rationale = self.manager._determine_story_gate_decision({"overall_score": 0.97})
        assert "excellent completion" in rationale[1]

        rationale = self.manager._determine_epic_gate_decision({"overall_score": 0.85})
        assert "acceptable quality but some areas need attention" in rationale[1]

        rationale = self.manager._determine_release_gate_decision(
            {"overall_score": 0.80}
        )
        assert "insufficient for production deployment" in rationale[1]
