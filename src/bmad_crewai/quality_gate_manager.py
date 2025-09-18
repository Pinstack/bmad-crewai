"""Quality gate and checklist management functionality."""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from .checklist_executor import ChecklistExecutor

logger = logging.getLogger(__name__)


class GateDecision(Enum):
    """Quality gate decision outcomes."""

    PASS = "PASS"
    CONCERNS = "CONCERNS"
    FAIL = "FAIL"


class GateType(Enum):
    """Types of quality gates."""

    STORY = "story"
    EPIC = "epic"
    SPRINT = "sprint"
    RELEASE = "release"


class QualityGateManager:
    """Manager for quality gates and checklist execution with enhanced PASS/CONCERNS/FAIL decision framework."""

    def __init__(self):
        self.checklist_executor = ChecklistExecutor()
        self.logger = logging.getLogger(__name__)

    def validate_gate_with_decision(
        self,
        checklist_id: str,
        gate_type: str = "story",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Enhanced gate validation with structured PASS/CONCERNS/FAIL decision framework.

        Args:
            checklist_id: ID of checklist to execute
            gate_type: Type of gate ('story', 'epic', 'sprint', 'release')
            context: Optional context data for validation

        Returns:
            Dict with comprehensive gate validation results including decision rationale
        """
        try:
            # Execute checklist
            execution_results = self.checklist_executor.execute_checklist(
                checklist_id, context
            )

            if "error" in execution_results:
                return execution_results

            # Determine gate decision based on execution results and gate type
            gate_decision, rationale = self._determine_gate_decision(
                execution_results, gate_type
            )

            # Build comprehensive gate results
            gate_results = {
                "gate_type": gate_type,
                "checklist_id": checklist_id,
                "decision": gate_decision.value,
                "decision_rationale": rationale,
                "execution_results": execution_results,
                "confidence_score": self._calculate_confidence_score(
                    execution_results, gate_type
                ),
                "critical_issues": self._identify_critical_issues(
                    execution_results, gate_type
                ),
                "recommendations": self._generate_gate_recommendations(
                    execution_results, gate_decision, gate_type
                ),
                "artefact_types_validated": self._extract_artefact_types(checklist_id),
            }

            self.logger.info(
                f"Quality gate {gate_type} validation completed: {gate_decision.value} "
                f"(confidence: {gate_results['confidence_score']:.1f})"
            )

            return gate_results

        except Exception as e:
            self.logger.error(f"Enhanced gate validation failed: {e}")
            return {"error": str(e)}

    def _determine_gate_decision(
        self, execution_results: Dict[str, Any], gate_type: str
    ) -> tuple[GateDecision, str]:
        """Determine gate decision based on execution results and gate-specific criteria.

        Args:
            execution_results: Results from checklist execution
            gate_type: Type of quality gate

        Returns:
            Tuple of (GateDecision, rationale_string)
        """
        overall_score = execution_results.get("overall_score", 0)

        # Gate-specific thresholds and criteria
        if gate_type == "story":
            return self._determine_story_gate_decision(execution_results)
        elif gate_type == "epic":
            return self._determine_epic_gate_decision(execution_results)
        elif gate_type == "sprint":
            return self._determine_sprint_gate_decision(execution_results)
        elif gate_type == "release":
            return self._determine_release_gate_decision(execution_results)
        else:
            # Default logic for unknown gate types
            if overall_score >= 0.9:
                return GateDecision.PASS, "Overall completion meets high standards"
            elif overall_score >= 0.7:
                return GateDecision.CONCERNS, "Acceptable completion with minor issues"
            else:
                return (
                    GateDecision.FAIL,
                    "Insufficient completion for quality standards",
                )

    def _determine_story_gate_decision(
        self, execution_results: Dict[str, Any]
    ) -> tuple[GateDecision, str]:
        """Determine story gate decision with focus on completeness and quality."""
        overall_score = execution_results.get("overall_score", 0)
        sections = execution_results.get("sections", {})

        # Story gates are strict - must meet high standards
        if overall_score >= 0.95:
            return (
                GateDecision.PASS,
                "Story meets all quality criteria with excellent completion",
            )
        elif overall_score >= 0.85:
            return (
                GateDecision.CONCERNS,
                "Story meets basic requirements but has minor quality issues",
            )
        else:
            return GateDecision.FAIL, "Story does not meet minimum quality standards"

    def _determine_epic_gate_decision(
        self, execution_results: Dict[str, Any]
    ) -> tuple[GateDecision, str]:
        """Determine epic gate decision with focus on comprehensive coverage."""
        overall_score = execution_results.get("overall_score", 0)

        # Epic gates allow some flexibility for complex multi-story work
        if overall_score >= 0.9:
            return (
                GateDecision.PASS,
                "Epic demonstrates comprehensive quality across all stories",
            )
        elif overall_score >= 0.75:
            return (
                GateDecision.CONCERNS,
                "Epic has acceptable quality but some areas need attention",
            )
        else:
            return GateDecision.FAIL, "Epic quality is insufficient for integration"

    def _determine_sprint_gate_decision(
        self, execution_results: Dict[str, Any]
    ) -> tuple[GateDecision, str]:
        """Determine sprint gate decision with focus on team velocity and consistency."""
        overall_score = execution_results.get("overall_score", 0)

        # Sprint gates balance quality with delivery velocity
        if overall_score >= 0.85:
            return (
                GateDecision.PASS,
                "Sprint delivers quality work with good team performance",
            )
        elif overall_score >= 0.7:
            return (
                GateDecision.CONCERNS,
                "Sprint acceptable but team should address quality issues",
            )
        else:
            return (
                GateDecision.FAIL,
                "Sprint quality is unacceptable and blocks progression",
            )

    def _determine_release_gate_decision(
        self, execution_results: Dict[str, Any]
    ) -> tuple[GateDecision, str]:
        """Determine release gate decision with highest quality bar."""
        overall_score = execution_results.get("overall_score", 0)

        # Release gates have the highest bar - no compromises
        if overall_score >= 0.98:
            return (
                GateDecision.PASS,
                "Release meets all quality requirements for production deployment",
            )
        elif overall_score >= 0.95:
            return (
                GateDecision.CONCERNS,
                "Release has minor issues that should be documented and tracked",
            )
        else:
            return (
                GateDecision.FAIL,
                "Release quality is insufficient for production deployment",
            )

    def _calculate_confidence_score(
        self, execution_results: Dict[str, Any], gate_type: str
    ) -> float:
        """Calculate confidence score for gate decision (0.0 to 1.0)."""
        base_score = execution_results.get("overall_score", 0)

        # Adjust confidence based on gate type and data completeness
        confidence_multiplier = 1.0

        if gate_type in ["release", "sprint"]:
            # Higher stakes gates need more confidence
            confidence_multiplier = 0.9

        # Reduce confidence if execution had errors or incomplete data
        sections = execution_results.get("sections", {})
        if not sections:
            confidence_multiplier *= 0.8

        return min(base_score * confidence_multiplier, 1.0)

    def _identify_critical_issues(
        self, execution_results: Dict[str, Any], gate_type: str
    ) -> List[Dict[str, Any]]:
        """Identify critical issues that impact gate decision."""
        critical_issues = []
        sections = execution_results.get("sections", [])

        # Handle both dict and list formats for sections
        if isinstance(sections, dict):
            sections_iter = sections.items()
        elif isinstance(sections, list):
            sections_iter = [
                (section.get("title", f"Section {i}"), section)
                for i, section in enumerate(sections)
            ]
        else:
            return critical_issues

        for section_name, section_data in sections_iter:
            failed_items = section_data.get("failed_items", [])
            if failed_items:
                is_critical = section_data.get("is_critical", False)
                critical_issues.append(
                    {
                        "section": section_name,
                        "failed_items": failed_items,
                        "severity": (
                            "high"
                            if (is_critical or len(failed_items) > 2)
                            else "medium"
                        ),
                    }
                )

        return critical_issues

    def _generate_gate_recommendations(
        self,
        execution_results: Dict[str, Any],
        gate_decision: GateDecision,
        gate_type: str,
    ) -> List[str]:
        """Generate actionable recommendations based on gate results."""
        recommendations = []

        if gate_decision == GateDecision.FAIL:
            recommendations.append(
                f"Address all failed checklist items before proceeding with {gate_type}"
            )
        elif gate_decision == GateDecision.CONCERNS:
            recommendations.append(
                f"Document and track the identified issues for {gate_type} completion"
            )

        overall_score = execution_results.get("overall_score", 0)
        if overall_score < 0.8:
            recommendations.append(
                "Consider additional quality practices or training for team improvement"
            )

        return recommendations

    def _extract_artefact_types(self, checklist_id: str) -> List[str]:
        """Extract artefact types that were validated in this checklist."""
        # This would be enhanced based on checklist content analysis
        # For now, return a basic mapping
        artefact_mapping = {
            "story-dod-checklist": ["story"],
            "architect-checklist": ["architecture"],
            "pm-checklist": ["prd", "epic"],
            "po-master-checklist": ["story", "epic"],
        }

        return artefact_mapping.get(checklist_id, ["unknown"])

    def test_quality_gates(self) -> Dict[str, Any]:
        """Test quality gate and checklist execution framework.

        Returns:
            Dict with quality gate test results
        """
        try:
            results = self.checklist_executor.test_checklist_execution()
            self.logger.info("Quality gates test completed")
            return results
        except Exception as e:
            self.logger.error(f"Quality gates test failed: {e}")
            return {"error": str(e)}

    def execute_checklist(
        self, checklist_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a quality checklist.

        Args:
            checklist_id: ID of checklist to execute
            context: Optional context data for validation

        Returns:
            Dict with execution results
        """
        try:
            results = self.checklist_executor.execute_checklist(checklist_id, context)
            self.logger.info(f"Checklist {checklist_id} executed successfully")
            return results
        except Exception as e:
            self.logger.error(f"Checklist execution failed: {e}")
            return {"error": str(e)}

    def validate_gate(
        self, checklist_id: str, gate_type: str = "story"
    ) -> Dict[str, Any]:
        """Validate a quality gate using a checklist.

        Args:
            checklist_id: Checklist to use for validation
            gate_type: Type of gate ('story', 'epic', 'sprint')

        Returns:
            Dict with gate validation results
        """
        # Use the enhanced validation framework for backward compatibility
        return self.validate_gate_with_decision(checklist_id, gate_type)

    def list_available_checklists(self) -> Dict[str, Dict[str, Any]]:
        """List all available checklists for quality gates.

        Returns:
            Dict with checklist information
        """
        try:
            return self.checklist_executor.list_checklists()
        except Exception as e:
            self.logger.error(f"Failed to list checklists: {e}")
            return {}

    def get_checklist_details(self, checklist_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific checklist.

        Args:
            checklist_id: ID of checklist to retrieve

        Returns:
            Dict with checklist details or None if not found
        """
        try:
            return self.checklist_executor.get_checklist(checklist_id)
        except Exception as e:
            self.logger.error(f"Failed to get checklist details: {e}")
            return None
