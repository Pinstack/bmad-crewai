"""Quality gate and checklist management functionality."""

import logging
import os
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

    def validate_artefact_generation_quality(
        self, artefact_type: str, content: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate the quality of generated artefacts.

        Args:
            artefact_type: Type of artefact to validate
            content: Artefact content to validate
            context: Optional context information

        Returns:
            Dict with quality validation results
        """
        results = {
            "artefact_type": artefact_type,
            "quality_score": 0.0,
            "issues": [],
            "strengths": [],
            "recommendations": [],
            "validation_criteria": [],
        }

        try:
            # Type-specific quality validation
            if artefact_type == "stories":
                results.update(self._validate_story_quality(content))
            elif artefact_type == "qa_gates":
                results.update(self._validate_gate_quality(content))
            elif artefact_type == "qa_assessments":
                results.update(self._validate_assessment_quality(content))
            elif artefact_type == "epics":
                results.update(self._validate_epic_quality(content))
            elif artefact_type == "prd":
                results.update(self._validate_prd_quality(content))
            else:
                results["issues"].append(f"Unknown artefact type: {artefact_type}")

            # Calculate overall quality score
            results["quality_score"] = self._calculate_artefact_quality_score(results)

            # Generate recommendations based on issues
            results["recommendations"] = self._generate_quality_recommendations(results)

        except Exception as e:
            results["issues"].append(f"Quality validation failed: {e}")
            results["quality_score"] = 0.0

        return results

    def validate_artefact_consistency(
        self,
        artefact_type: str,
        content: str,
        related_artefacts: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Validate artefact consistency across the document set.

        Args:
            artefact_type: Type of artefact to validate
            content: Artefact content to validate
            related_artefacts: Dict of related artefact types and their content

        Returns:
            Dict with consistency validation results
        """
        results = {
            "artefact_type": artefact_type,
            "consistency_score": 1.0,  # Start with perfect consistency
            "consistency_issues": [],
            "cross_references": [],
            "missing_links": [],
            "recommendations": [],
        }

        try:
            # Check for broken internal references
            results.update(self._validate_internal_references(content))

            # Validate cross-artefact consistency if related artefacts provided
            if related_artefacts:
                results.update(
                    self._validate_cross_artefact_consistency(
                        artefact_type, content, related_artefacts
                    )
                )

            # Check naming conventions and file references
            results.update(self._validate_reference_consistency(artefact_type, content))

        except Exception as e:
            results["consistency_issues"].append(f"Consistency validation failed: {e}")
            results["consistency_score"] = 0.0

        return results

    def _validate_story_quality(self, content: str) -> Dict[str, Any]:
        """Validate story artefact quality."""
        issues = []
        strengths = []
        criteria = [
            "has_status",
            "has_story_statement",
            "has_acceptance_criteria",
            "proper_format",
        ]

        # Check required sections
        if "## Status:" not in content:
            issues.append("Missing Status section")
        else:
            strengths.append("Has proper status tracking")

        if "## Story" not in content or "**As a**" not in content:
            issues.append("Missing or malformed story statement")
        else:
            strengths.append("Has well-formed user story")

        if "## Acceptance Criteria" not in content:
            issues.append("Missing acceptance criteria")
        else:
            strengths.append("Has acceptance criteria defined")

        # Check for proper markdown formatting
        if not content.strip().startswith("# "):
            issues.append("Does not start with proper markdown header")
        else:
            strengths.append("Proper markdown formatting")

        return {
            "issues": issues,
            "strengths": strengths,
            "validation_criteria": criteria,
        }

    def _validate_gate_quality(self, content: str) -> Dict[str, Any]:
        """Validate quality gate artefact quality."""
        issues = []
        strengths = []
        criteria = ["has_schema", "has_decision", "has_rationale", "proper_yaml"]

        # Check for required YAML fields
        if "schema:" not in content.lower():
            issues.append("Missing schema field")
        else:
            strengths.append("Has schema definition")

        if "gate:" not in content.lower():
            issues.append("Missing gate decision")
        else:
            strengths.append("Has gate decision")

        if "reviewer:" not in content.lower():
            issues.append("Missing reviewer information")
        else:
            strengths.append("Has reviewer attribution")

        return {
            "issues": issues,
            "strengths": strengths,
            "validation_criteria": criteria,
        }

    def _validate_assessment_quality(self, content: str) -> Dict[str, Any]:
        """Validate assessment artefact quality."""
        issues = []
        strengths = []
        criteria = ["has_structure", "has_findings", "has_date", "proper_format"]

        # Check for basic structure
        if not ("#" in content and "##" in content):
            issues.append("Missing proper heading structure")
        else:
            strengths.append("Has proper heading structure")

        # Check for date in filename or content
        has_date = any(
            indicator in content.lower()
            for indicator in ["date:", "updated:", "2024", "2025"]
        )
        if not has_date:
            issues.append("Missing date information")
        else:
            strengths.append("Has date tracking")

        return {
            "issues": issues,
            "strengths": strengths,
            "validation_criteria": criteria,
        }

    def _validate_epic_quality(self, content: str) -> Dict[str, Any]:
        """Validate epic artefact quality."""
        issues = []
        strengths = []
        criteria = ["has_goal", "has_stories", "has_acceptance", "proper_format"]

        if "## Epic Goal" not in content and "**Epic Goal**" not in content:
            issues.append("Missing epic goal statement")
        else:
            strengths.append("Has clear epic goal")

        if "## Story" not in content:
            issues.append("Missing story definitions")
        else:
            strengths.append("Has story breakdown")

        return {
            "issues": issues,
            "strengths": strengths,
            "validation_criteria": criteria,
        }

    def _validate_prd_quality(self, content: str) -> Dict[str, Any]:
        """Validate PRD artefact quality."""
        issues = []
        strengths = []
        criteria = [
            "has_overview",
            "has_requirements",
            "has_acceptance",
            "proper_format",
        ]

        # Basic PRD checks
        if len(content) < 500:  # Very basic length check
            issues.append("PRD content appears too brief")
        else:
            strengths.append("Has substantial content")

        if "## " not in content:
            issues.append("Missing section structure")
        else:
            strengths.append("Has proper section structure")

        return {
            "issues": issues,
            "strengths": strengths,
            "validation_criteria": criteria,
        }

    def _calculate_artefact_quality_score(
        self, validation_results: Dict[str, Any]
    ) -> float:
        """Calculate overall quality score from validation results."""
        issues = validation_results.get("issues", [])
        strengths = validation_results.get("strengths", [])
        criteria = validation_results.get("validation_criteria", [])

        if not criteria:
            return 0.0

        # Base score from criteria met
        criteria_met = len(strengths)
        total_criteria = len(criteria)
        base_score = criteria_met / total_criteria if total_criteria > 0 else 0

        # Penalty for issues
        issue_penalty = len(issues) * 0.1  # 10% penalty per issue
        final_score = max(0.0, min(1.0, base_score - issue_penalty))

        return final_score

    def _generate_quality_recommendations(
        self, validation_results: Dict[str, Any]
    ) -> List[str]:
        """Generate quality improvement recommendations."""
        recommendations = []
        issues = validation_results.get("issues", [])

        for issue in issues:
            if "missing" in issue.lower():
                recommendations.append(
                    f"Add {issue.lower().replace('missing', '').strip()}"
                )
            elif "malformed" in issue.lower():
                recommendations.append(
                    f"Fix formatting of {issue.lower().replace('malformed', '').strip()}"
                )
            else:
                recommendations.append(f"Address: {issue}")

        return recommendations

    def _validate_internal_references(self, content: str) -> Dict[str, Any]:
        """Validate internal references within artefact."""
        results = {"consistency_issues": [], "cross_references": []}

        # Check for broken markdown links
        import re

        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)

        for link_text, link_target in links:
            results["cross_references"].append(f"Link: {link_text} -> {link_target}")

            # Basic validation - could be enhanced with actual file existence checks
            if link_target.startswith("docs/") and not os.path.exists(link_target):
                results["consistency_issues"].append(
                    f"Potentially broken link: {link_target}"
                )

        return results

    def _validate_cross_artefact_consistency(
        self, artefact_type: str, content: str, related_artefacts: Dict[str, str]
    ) -> Dict[str, Any]:
        """Validate consistency between related artefacts."""
        results = {"consistency_issues": []}

        # Example: Check if story references exist in related epic
        if artefact_type == "stories" and "epics" in related_artefacts:
            epic_content = related_artefacts["epics"]
            # Simple check - story should reference its epic
            if "epic" not in content.lower():
                results["consistency_issues"].append(
                    "Story does not reference its parent epic"
                )

        return results

    def _validate_reference_consistency(
        self, artefact_type: str, content: str
    ) -> Dict[str, Any]:
        """Validate reference consistency within artefact type."""
        results = {"consistency_issues": []}

        # Check for consistent naming patterns
        if artefact_type == "stories":
            # Stories should follow naming conventions
            if not (content.startswith("# Story") or "## Story" in content):
                results["consistency_issues"].append("Inconsistent story header format")

        return results

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
