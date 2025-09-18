"""Checklist execution framework for BMAD quality gates."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChecklistExecutor:
    """Executes BMAD checklists and validates quality gates.

    This component loads checklists from .bmad-core/checklists/ and provides
    execution framework for quality gate validation.
    """

    def __init__(self, checklists_path: Optional[str] = None):
        """Initialize checklist executor.

        Args:
            checklists_path: Path to checklists directory
                           (defaults to .bmad-core/checklists/)
        """
        self.checklists_path = Path(checklists_path or ".bmad-core/checklists")
        self.checklists = {}
        self.logger = logging.getLogger(__name__)

        self._load_checklists()

    def _load_checklists(self):
        """Load all available checklists."""
        if not self.checklists_path.exists():
            self.logger.warning(
                f"Checklists directory not found: {self.checklists_path}"
            )
            return

        for checklist_file in self.checklists_path.glob("*.md"):
            try:
                checklist_id = checklist_file.stem
                content = checklist_file.read_text(encoding="utf-8")
                self.checklists[checklist_id] = self._parse_checklist(content)
                self.logger.debug(f"Loaded checklist: {checklist_id}")
            except Exception as e:
                self.logger.error(f"Failed to load checklist {checklist_file}: {e}")

        self.logger.info(f"Loaded {len(self.checklists)} checklists")

    def _parse_checklist(self, content: str) -> Dict[str, Any]:
        """Parse checklist markdown content into structured format.

        Args:
            content: Raw markdown content

        Returns:
            Dict containing parsed checklist structure
        """
        lines = content.split("\n")
        checklist = {"title": "", "sections": [], "items": []}

        current_section = None

        for line in lines:
            line = line.strip()

            # Extract title
            if line.startswith("# ") and not checklist["title"]:
                checklist["title"] = line[2:].strip()
                continue

            # Detect section headers
            if line.startswith("## "):
                if current_section:
                    checklist["sections"].append(current_section)

                current_section = {"title": line[3:].strip(), "items": []}
                continue

            # Parse checklist items
            if (
                line.startswith("- [ ]")
                or line.startswith("- [x]")
                or line.startswith("- [X]")
            ):
                item_text = line[5:].strip()
                item = {
                    "text": item_text,
                    "checked": line.startswith("- [x]") or line.startswith("- [X]"),
                    "section": current_section["title"] if current_section else None,
                }
                checklist["items"].append(item)

                if current_section:
                    current_section["items"].append(item)

        # Add final section
        if current_section:
            checklist["sections"].append(current_section)

        return checklist

    def list_checklists(self) -> Dict[str, Dict[str, Any]]:
        """List all available checklists with basic information.

        Returns:
            Dict mapping checklist IDs to summary information
        """
        return {
            checklist_id: {
                "title": info["title"],
                "sections": len(info["sections"]),
                "items": len(info["items"]),
            }
            for checklist_id, info in self.checklists.items()
        }

    def get_checklist(self, checklist_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific checklist by ID.

        Args:
            checklist_id: Checklist identifier

        Returns:
            Checklist data or None if not found
        """
        return self.checklists.get(checklist_id)

    def execute_checklist(
        self, checklist_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a checklist and return validation results.

        Args:
            checklist_id: Checklist to execute
            context: Optional context data for validation

        Returns:
            Dict containing execution results
        """
        checklist = self.get_checklist(checklist_id)
        if not checklist:
            return {"success": False, "error": f"Checklist not found: {checklist_id}"}

        results = {
            "checklist_id": checklist_id,
            "checklist_title": checklist["title"],
            "total_items": len(checklist["items"]),
            "sections": {},
            "overall_score": 0,
            "recommendations": [],
        }

        # Process each section
        for section in checklist["sections"]:
            section_results = self._execute_section(section, context)
            results["sections"][section["title"]] = section_results

            # Update overall score
            if section_results["total_items"] > 0:
                section_score = (
                    section_results["completed_items"] / section_results["total_items"]
                )
                results["overall_score"] += section_score

        # Calculate final score
        if checklist["sections"]:
            results["overall_score"] /= len(checklist["sections"])

        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(results)

        # Determine gate decision
        results["gate_decision"] = self._determine_gate_decision(results)

        self.logger.info(
            f"Checklist {checklist_id} executed with score: "
            f"{results['overall_score']:.2f}"
        )
        return results

    def _execute_section(
        self, section: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a single section of a checklist.

        Args:
            section: Section data
            context: Optional context for validation

        Returns:
            Section execution results
        """
        results = {
            "section_title": section["title"],
            "total_items": len(section["items"]),
            "completed_items": 0,
            "failed_items": [],
            "notes": [],
        }

        for item in section["items"]:
            # Basic validation - in a real implementation, this would be
            # more sophisticated
            is_completed = self._validate_checklist_item(item, context)

            if is_completed:
                results["completed_items"] += 1
            else:
                results["failed_items"].append(item["text"])

        return results

    def _validate_checklist_item(
        self, item: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> bool:
        """Validate a single checklist item.

        Args:
            item: Checklist item
            context: Validation context

        Returns:
            True if item passes validation
        """
        # For now, use the item's checked status
        # In a real implementation, this would perform actual validation
        return item.get("checked", False)

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on execution results.

        Args:
            results: Execution results

        Returns:
            List of recommendations
        """
        recommendations = []

        if results["overall_score"] < 0.8:
            recommendations.append(
                "Overall completion is below 80%. Consider reviewing failed items."
            )

        for section_name, section_results in results["sections"].items():
            if section_results["completed_items"] < section_results["total_items"]:
                failed_count = (
                    section_results["total_items"] - section_results["completed_items"]
                )
                recommendations.append(
                    f"Section '{section_name}' has {failed_count} incomplete "
                    f"items that need attention."
                )

        if not recommendations:
            recommendations.append(
                "All checklist items completed successfully. Ready for quality gate."
            )

        return recommendations

    def _determine_gate_decision(self, results: Dict[str, Any]) -> str:
        """Determine quality gate decision based on results.

        Args:
            results: Execution results

        Returns:
            Gate decision: 'PASS', 'CONCERNS', or 'FAIL'
        """
        score = results["overall_score"]

        if score >= 0.9:
            return "PASS"
        elif score >= 0.7:
            return "CONCERNS"
        else:
            return "FAIL"

    def validate_quality_gate(
        self, checklist_id: str, gate_type: str = "story"
    ) -> Dict[str, Any]:
        """Validate a quality gate using the appropriate checklist.

        Args:
            checklist_id: Checklist to use for validation
            gate_type: Type of gate ('story', 'epic', 'sprint')

        Returns:
            Gate validation results
        """
        # Execute checklist
        execution_results = self.execute_checklist(checklist_id)

        # Add gate-specific information
        gate_results = {
            "gate_type": gate_type,
            "checklist_id": checklist_id,
            "timestamp": "2025-09-17T12:00:00Z",  # Would use datetime.now()
            # in real implementation
            "execution_results": execution_results,
        }

        # Generate gate decision
        gate_results["decision"] = execution_results.get("gate_decision", "UNKNOWN")
        gate_results["confidence"] = self._calculate_confidence(gate_results)

        self.logger.info(
            f"Quality gate {gate_type} validation completed: {gate_results['decision']}"
        )
        return gate_results

    def _calculate_confidence(self, gate_results: Dict[str, Any]) -> str:
        """Calculate confidence level for gate decision.

        Args:
            gate_results: Gate validation results

        Returns:
            Confidence level: 'HIGH', 'MEDIUM', or 'LOW'
        """
        execution = gate_results.get("execution_results", {})
        score = execution.get("overall_score", 0)

        if score >= 0.9:
            return "HIGH"
        elif score >= 0.7:
            return "MEDIUM"
        else:
            return "LOW"

    def test_checklist_execution(self) -> Dict[str, bool]:
        """Test checklist execution functionality.

        Returns:
            Dict with test results
        """
        results = {
            "checklist_loading": False,
            "checklist_parsing": False,
            "checklist_execution": False,
            "gate_validation": False,
        }

        try:
            # Test checklist loading
            if self.checklists:
                results["checklist_loading"] = True

                # Test checklist parsing
                checklist = list(self.checklists.values())[0]
                if checklist.get("title") and checklist.get("items"):
                    results["checklist_parsing"] = True

                    # Test checklist execution
                    execution_results = self.execute_checklist(
                        list(self.checklists.keys())[0]
                    )
                    if "overall_score" in execution_results:
                        results["checklist_execution"] = True

                        # Test gate validation
                        gate_results = self.validate_quality_gate(
                            list(self.checklists.keys())[0]
                        )
                        if "decision" in gate_results:
                            results["gate_validation"] = True

            self.logger.info("Checklist execution tests completed")

        except Exception as e:
            self.logger.error(f"Checklist execution test failed: {e}")

        return results
