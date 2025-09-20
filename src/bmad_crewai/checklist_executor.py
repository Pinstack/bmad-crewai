"""Checklist execution framework for BMAD quality gates."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ChecklistExecutor:
    """Executes BMAD checklists and validates quality gates with artefact-specific validation.

    This component loads checklists from .bmad-core/checklists/ and provides
    enhanced execution framework for quality gate validation with support for
    different artefact types and validation rules.
    """

    # Artefact type mappings for enhanced validation
    ARTEFACT_TYPES = {
        "story": ["user_story", "acceptance_criteria", "tasks", "testing"],
        "epic": [
            "epic_definition",
            "story_list",
            "acceptance_criteria",
            "dependencies",
        ],
        "architecture": ["system_design", "component_diagram", "data_flow", "security"],
        "prd": [
            "requirements",
            "user_stories",
            "acceptance_criteria",
            "success_metrics",
        ],
        "qa_report": ["test_results", "coverage", "issues", "recommendations"],
    }

    def __init__(self, checklists_path: Optional[str] = None):
        """Initialize checklist executor.

        Args:
            checklists_path: Path to checklists directory
                           (defaults to .bmad-core/checklists/)
        """
        self.checklists_path = Path(checklists_path or ".bmad-core/checklists")
        self.checklists = {}
        self.logger = logging.getLogger(__name__)

        # Enhanced validation rules
        self.validation_rules = self._initialize_validation_rules()

        self._load_checklists()

    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Initialize enhanced validation rules for different artefact types."""
        return {
            "artefact_detection": {
                "story": self._detect_story_artefact,
                "epic": self._detect_epic_artefact,
                "architecture": self._detect_architecture_artefact,
                "prd": self._detect_prd_artefact,
            },
            "acceptance_thresholds": {
                "story": 0.95,  # Stories need high completion
                "epic": 0.90,  # Epics allow some flexibility
                "architecture": 0.92,  # Architecture needs thorough validation
                "prd": 0.88,  # PRDs can have some gaps for iteration
            },
            "critical_sections": {
                "story": ["acceptance_criteria", "testing"],
                "epic": ["story_list", "acceptance_criteria"],
                "architecture": ["system_design", "security"],
                "prd": ["requirements", "success_metrics"],
            },
        }

    def detect_artefact_type(self, artefact_content: str) -> str:
        """Detect the type of artefact from its content.

        Args:
            artefact_content: Content of the artefact to analyze

        Returns:
            Detected artefact type or 'unknown'
        """
        for artefact_type, detector in self.validation_rules[
            "artefact_detection"
        ].items():
            if detector(artefact_content):
                return artefact_type

        return "unknown"

    def _detect_story_artefact(self, content: str) -> bool:
        """Detect if content is a user story."""
        indicators = [
            "## Story",
            "## Acceptance Criteria",
            "## Tasks",
            "As a",
            "I want",
        ]
        return any(indicator in content for indicator in indicators)

    def _detect_epic_artefact(self, content: str) -> bool:
        """Detect if content is an epic."""
        indicators = ["## Epic", "## Stories", "Epic Goal", "Story List"]
        return any(indicator in content for indicator in indicators)

    def _detect_architecture_artefact(self, content: str) -> bool:
        """Detect if content is architecture documentation."""
        indicators = [
            "## Architecture",
            "## System Design",
            "## Component",
            "Technical Summary",
        ]
        return any(indicator in content for indicator in indicators)

    def _detect_prd_artefact(self, content: str) -> bool:
        """Detect if content is a PRD."""
        indicators = [
            "## Product Requirements",
            "## Functional Requirements",
            "## User Personas",
        ]
        return any(indicator in content for indicator in indicators)

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
        """Execute a checklist and return validation results with artefact-specific enhancements.

        Args:
            checklist_id: Checklist to execute
            context: Optional context data for validation

        Returns:
            Dict containing execution results
        """
        checklist = self.get_checklist(checklist_id)
        if not checklist:
            return {"success": False, "error": f"Checklist not found: {checklist_id}"}

        # Detect artefact type from context if available
        artefact_type = "unknown"
        if context and "artefact_content" in context:
            artefact_type = self.detect_artefact_type(context["artefact_content"])

        results = {
            "checklist_id": checklist_id,
            "checklist_title": checklist["title"],
            "total_items": len(checklist["items"]),
            "artefact_type": artefact_type,
            "sections": {},
            "overall_score": 0,
            "acceptance_threshold": self.validation_rules["acceptance_thresholds"].get(
                artefact_type, 0.8
            ),
            "recommendations": [],
            "artefact_specific_findings": [],
        }

        # Process each section with artefact-specific validation
        for section in checklist["sections"]:
            section_results = self._execute_section_enhanced(
                section, context, artefact_type
            )
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

        # Add artefact-specific findings
        results["artefact_specific_findings"] = self._generate_artefact_findings(
            results, artefact_type
        )

        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(results)

        # Determine gate decision with artefact-specific thresholds
        results["gate_decision"] = self._determine_gate_decision_enhanced(
            results, artefact_type
        )

        self.logger.info(
            f"Checklist {checklist_id} executed for {artefact_type} artefact with score: "
            f"{results['overall_score']:.2f}"
        )
        return results

    def _execute_section_enhanced(
        self,
        section: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        artefact_type: str,
    ) -> Dict[str, Any]:
        """Execute a single section with artefact-specific validation enhancements.

        Args:
            section: Section data
            context: Optional context for validation
            artefact_type: Type of artefact being validated

        Returns:
            Section execution results with artefact-specific insights
        """
        # Use the existing section execution as base
        results = self._execute_section(section, context)

        # Add artefact-specific validation
        results["artefact_validation"] = self._validate_section_for_artefact(
            section, artefact_type, context
        )

        # Enhance scoring based on artefact criticality
        critical_sections = self.validation_rules["critical_sections"].get(
            artefact_type, []
        )
        section_name_lower = section["title"].lower().replace(" ", "_")

        if any(critical in section_name_lower for critical in critical_sections):
            results["is_critical"] = True
            results["critical_weight"] = 1.5  # Weight critical sections more heavily
        else:
            results["is_critical"] = False
            results["critical_weight"] = 1.0

        return results

    def _validate_section_for_artefact(
        self,
        section: Dict[str, Any],
        artefact_type: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Perform artefact-specific validation for a section.

        Args:
            section: Section data
            artefact_type: Type of artefact
            context: Validation context

        Returns:
            Artefact-specific validation results
        """
        validation_results = {
            "artefact_compliance": True,
            "specific_findings": [],
            "validation_rules_applied": [],
        }

        # Apply artefact-specific validation rules
        if artefact_type == "story":
            validation_results.update(self._validate_story_section(section, context))
        elif artefact_type == "epic":
            validation_results.update(self._validate_epic_section(section, context))
        elif artefact_type == "architecture":
            validation_results.update(
                self._validate_architecture_section(section, context)
            )
        elif artefact_type == "prd":
            validation_results.update(self._validate_prd_section(section, context))

        return validation_results

    def _validate_story_section(
        self, section: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate story-specific requirements in a section."""
        findings = []
        section_title = section["title"].lower()

        if "acceptance criteria" in section_title:
            # Check for measurable criteria
            for item in section["items"]:
                if not any(
                    word in item["text"].lower()
                    for word in ["should", "must", "can", "will"]
                ):
                    findings.append(
                        f"Acceptance criterion lacks clear success indicator: {item['text']}"
                    )

        elif "testing" in section_title:
            # Check for test coverage completeness
            test_types = ["unit", "integration", "acceptance"]
            mentioned_types = []
            for item in section["items"]:
                for test_type in test_types:
                    if test_type in item["text"].lower():
                        mentioned_types.append(test_type)

            missing_types = set(test_types) - set(mentioned_types)
            if missing_types:
                findings.append(f"Missing test types: {', '.join(missing_types)}")

        return {
            "validation_rules_applied": [
                "acceptance_criteria_clarity",
                "test_coverage_completeness",
            ],
            "specific_findings": findings,
        }

    def _validate_epic_section(
        self, section: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate epic-specific requirements in a section."""
        findings = []
        section_title = section["title"].lower()

        if "story list" in section_title:
            # Check for story completeness
            story_count = len(
                [item for item in section["items"] if "story" in item["text"].lower()]
            )
            if story_count == 0:
                findings.append("No stories defined in epic")

        elif "dependencies" in section_title:
            # Check for dependency clarity
            for item in section["items"]:
                if "depends on" in item["text"].lower() and not any(
                    word in item["text"].lower() for word in ["story", "epic", "system"]
                ):
                    findings.append(f"Unclear dependency: {item['text']}")

        return {
            "validation_rules_applied": ["story_completeness", "dependency_clarity"],
            "specific_findings": findings,
        }

    def _validate_architecture_section(
        self, section: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate architecture-specific requirements in a section."""
        findings = []
        section_title = section["title"].lower()

        if "security" in section_title:
            # Check for security considerations
            security_aspects = [
                "authentication",
                "authorization",
                "encryption",
                "validation",
            ]
            mentioned_aspects = []
            for item in section["items"]:
                for aspect in security_aspects:
                    if aspect in item["text"].lower():
                        mentioned_aspects.append(aspect)

            if len(mentioned_aspects) < 2:
                findings.append(
                    "Limited security coverage - consider additional security aspects"
                )

        elif "system design" in section_title:
            # Check for design completeness
            design_elements = ["components", "interfaces", "data flow", "deployment"]
            mentioned_elements = []
            for item in section["items"]:
                for element in design_elements:
                    if element in item["text"].lower():
                        mentioned_elements.append(element)

            missing_elements = set(design_elements) - set(mentioned_elements)
            if missing_elements:
                findings.append(
                    f"Missing design elements: {', '.join(missing_elements)}"
                )

        return {
            "validation_rules_applied": ["security_coverage", "design_completeness"],
            "specific_findings": findings,
        }

    def _validate_prd_section(
        self, section: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate PRD-specific requirements in a section."""
        findings = []
        section_title = section["title"].lower()

        if "requirements" in section_title:
            # Check for requirement clarity
            for item in section["items"]:
                if len(item["text"]) < 20:  # Very short requirements
                    findings.append(f"Requirement too vague: {item['text']}")

        elif "success metrics" in section_title:
            # Check for measurable metrics
            for item in section["items"]:
                if not any(
                    word in item["text"].lower()
                    for word in ["measure", "track", "metric", "kpi", "%", "count"]
                ):
                    findings.append(f"Non-measurable metric: {item['text']}")

        return {
            "validation_rules_applied": ["requirement_clarity", "metric_measurability"],
            "specific_findings": findings,
        }

    def _generate_artefact_findings(
        self, results: Dict[str, Any], artefact_type: str
    ) -> List[Dict[str, Any]]:
        """Generate artefact-specific findings and recommendations."""
        findings = []

        # Collect findings from all sections
        for section_name, section_data in results["sections"].items():
            artefact_validation = section_data.get("artefact_validation", {})
            specific_findings = artefact_validation.get("specific_findings", [])

            for finding in specific_findings:
                findings.append(
                    {
                        "section": section_name,
                        "artefact_type": artefact_type,
                        "finding": finding,
                        "severity": "medium",  # Default severity
                        "recommendation": self._generate_finding_recommendation(
                            finding, artefact_type
                        ),
                    }
                )

        return findings

    def _generate_finding_recommendation(self, finding: str, artefact_type: str) -> str:
        """Generate a recommendation based on a specific finding."""
        # Simple rule-based recommendations
        if "acceptance criterion" in finding.lower():
            return (
                "Review and clarify acceptance criteria to ensure they are "
                "measurable and testable"
            )
        elif "test" in finding.lower():
            return f"Add {artefact_type}-appropriate testing coverage for complete validation"
        elif "security" in finding.lower():
            return "Enhance security considerations with additional validation layers"
        elif "design" in finding.lower():
            return "Complete architecture design with missing elements for comprehensive coverage"
        elif "requirement" in finding.lower():
            return "Refine requirements for clarity and completeness"
        elif "metric" in finding.lower():
            return "Define measurable success metrics with clear tracking mechanisms"
        else:
            return "Review and enhance based on artefact-specific best practices"

    def _determine_gate_decision_enhanced(
        self, results: Dict[str, Any], artefact_type: str
    ) -> str:
        """Determine gate decision with artefact-specific thresholds and critical
        section weighting."""
        overall_score = results.get("overall_score", 0)
        acceptance_threshold = results.get("acceptance_threshold", 0.8)

        # Apply critical section weighting
        critical_sections = self.validation_rules["critical_sections"].get(
            artefact_type, []
        )
        critical_score = 0
        critical_count = 0

        for section_name, section_data in results["sections"].items():
            section_name_lower = section_name.lower().replace(" ", "_")
            if any(critical in section_name_lower for critical in critical_sections):
                if section_data["total_items"] > 0:
                    section_score = (
                        section_data["completed_items"] / section_data["total_items"]
                    )
                    critical_score += section_score
                    critical_count += 1

        # Adjust overall score based on critical sections
        if critical_count > 0:
            critical_avg = critical_score / critical_count
            # Critical sections have 40% influence on final decision
            weighted_score = (overall_score * 0.6) + (critical_avg * 0.4)
        else:
            weighted_score = overall_score

        # Apply artefact-specific thresholds
        if weighted_score >= acceptance_threshold:
            if weighted_score >= acceptance_threshold + 0.05:  # Excellent performance
                return "PASS"
            else:  # Good performance
                return "CONCERNS"
        else:
            return "FAIL"

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
        """Validate a single checklist item with enhanced rules and acceptance criteria.

        Args:
            item: Checklist item
            context: Validation context

        Returns:
            True if item passes validation
        """
        # Enhanced validation with configurable rules
        validation_result = self._apply_validation_rules(item, context)

        # Log validation details for transparency
        if not validation_result["passed"]:
            self.logger.debug(
                f"Item validation failed: {item['text']} - {validation_result['reason']}"
            )

        return validation_result["passed"]

    def _apply_validation_rules(
        self, item: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply configurable validation rules to a checklist item.

        Args:
            item: Checklist item to validate
            context: Validation context

        Returns:
            Dict with validation result and reasoning
        """
        item_text = item.get("text", "").lower()
        section_title = item.get("section", "").lower()

        # Rule 1: Basic completion check (fallback to checked status)
        if not item.get("checked", False):
            return {
                "passed": False,
                "reason": "Item is not marked as completed",
                "rule": "basic_completion",
            }

        # Rule 2: Content quality validation
        quality_check = self._validate_content_quality(
            item_text, section_title, context
        )
        if not quality_check["passed"]:
            return quality_check

        # Rule 3: Context-aware validation
        if context:
            context_check = self._validate_context_requirements(item, context)
            if not context_check["passed"]:
                return context_check

        # Rule 4: Artefact-specific validation
        if context and "artefact_type" in context:
            artefact_check = self._validate_artefact_specific_rules(
                item, context["artefact_type"]
            )
            if not artefact_check["passed"]:
                return artefact_check

        return {
            "passed": True,
            "reason": "All validation rules passed",
            "rule": "comprehensive_validation",
        }

    def _validate_content_quality(
        self, item_text: str, section_title: str, context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate content quality and completeness of checklist items.

        Args:
            item_text: The checklist item text
            section_title: Title of the section containing the item
            context: Validation context

        Returns:
            Validation result
        """
        # Rule: Items must have meaningful content
        if len(item_text.strip()) < 5:
            return {
                "passed": False,
                "reason": "Item text is too short or vague",
                "rule": "content_quality_minimum_length",
            }

        # Rule: Acceptance criteria should be measurable
        if "acceptance criteria" in section_title or "ac" in section_title:
            measurable_indicators = [
                "should",
                "must",
                "can",
                "will",
                "able to",
                "verify",
            ]
            if not any(indicator in item_text for indicator in measurable_indicators):
                return {
                    "passed": False,
                    "reason": "Acceptance criterion lacks measurable success indicators",
                    "rule": "acceptance_criteria_measurable",
                }

        # Rule: Testing items should specify test types
        if "testing" in section_title or "test" in section_title:
            test_indicators = ["unit", "integration", "e2e", "acceptance", "manual"]
            if not any(indicator in item_text for indicator in test_indicators):
                return {
                    "passed": False,
                    "reason": "Testing item should specify test type or approach",
                    "rule": "testing_specification_required",
                }

        # Rule: Security items should address specific concerns
        if "security" in section_title:
            security_indicators = [
                "authentication",
                "authorization",
                "encryption",
                "validation",
                "injection",
                "xss",
                "csrf",
                "privacy",
                "audit",
            ]
            if not any(indicator in item_text for indicator in security_indicators):
                return {
                    "passed": False,
                    "reason": "Security item should address specific security concerns",
                    "rule": "security_concerns_specific",
                }

        return {
            "passed": True,
            "reason": "Content quality validation passed",
            "rule": "content_quality_checks",
        }

    def _validate_context_requirements(
        self, item: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate checklist items against context requirements.

        Args:
            item: Checklist item
            context: Validation context

        Returns:
            Validation result
        """
        item_text = item.get("text", "").lower()

        # Context: Artefact content validation
        if "artefact_content" in context:
            artefact_content = context["artefact_content"].lower()

            # Rule: References in checklist should exist in artefact
            if "reference" in item_text or "see" in item_text:
                # Extract potential references and check if they exist
                if "section" in item_text and not any(
                    section in artefact_content for section in ["##", "###"]
                ):
                    return {
                        "passed": False,
                        "reason": "Referenced sections should exist in artefact",
                        "rule": "reference_validation",
                    }

        # Context: Previous validation results
        if "previous_results" in context:
            prev_results = context["previous_results"]

            # Rule: Regression checks for repeated validations
            if prev_results.get("gate_decision") == "FAIL":
                # Be more strict on re-validation
                if len(item_text.split()) < 3:  # Very brief items
                    return {
                        "passed": False,
                        "reason": "Previous validation failed - items must be more detailed",
                        "rule": "regression_prevention",
                    }

        return {
            "passed": True,
            "reason": "Context requirements validation passed",
            "rule": "context_validation",
        }

    def _validate_artefact_specific_rules(
        self, item: Dict[str, Any], artefact_type: str
    ) -> Dict[str, Any]:
        """Apply artefact-specific validation rules.

        Args:
            item: Checklist item
            artefact_type: Type of artefact being validated

        Returns:
            Validation result
        """
        item_text = item.get("text", "").lower()

        if artefact_type == "story":
            # Stories require clear user value
            if "as a" in item_text and "i want" in item_text:
                if not any(word in item_text for word in ["so that", "to", "value"]):
                    return {
                        "passed": False,
                        "reason": "Story should clearly state the value or benefit",
                        "rule": "story_value_statement",
                    }

        elif artefact_type == "architecture":
            # Architecture items should be technical
            technical_indicators = [
                "component",
                "interface",
                "data",
                "security",
                "performance",
                "scalability",
                "deployment",
                "infrastructure",
            ]
            if not any(indicator in item_text for indicator in technical_indicators):
                return {
                    "passed": False,
                    "reason": "Architecture items should address technical concerns",
                    "rule": "architecture_technical_focus",
                }

        elif artefact_type == "prd":
            # PRD items should be user-focused
            user_indicators = [
                "user",
                "customer",
                "persona",
                "experience",
                "feature",
                "requirement",
            ]
            if not any(indicator in item_text for indicator in user_indicators):
                return {
                    "passed": False,
                    "reason": "PRD items should focus on user needs and requirements",
                    "rule": "prd_user_focus",
                }

        return {
            "passed": True,
            "reason": "Artefact-specific validation passed",
            "rule": "artefact_specific_rules",
        }

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

    def determine_gate_decision(
        self, results: Dict[str, Any], gate_type: str
    ) -> Tuple[str, str]:
        """Authority API for computing PASS/CONCERNS/FAIL gate decisions.

        This is the single authoritative source for gate decisions across the system.
        Uses gate-type-specific thresholds while maintaining consistent policy.

        Args:
            results: Execution results from checklist execution
            gate_type: Type of gate ('story', 'epic', 'sprint', 'release')

        Returns:
            Tuple of (decision, rationale) where:
            - decision: 'PASS', 'CONCERNS', or 'FAIL'
            - rationale: Human-readable explanation of the decision
        """
        overall_score = results.get("overall_score", 0)

        # Gate-type-specific thresholds (unchanged from QualityGateManager)
        if gate_type == "story":
            if overall_score >= 0.95:
                return (
                    "PASS",
                    "Story meets all quality criteria with excellent completion",
                )
            elif overall_score >= 0.85:
                return (
                    "CONCERNS",
                    "Story meets basic requirements but has minor quality issues",
                )
            else:
                return "FAIL", "Story does not meet minimum quality standards"

        elif gate_type == "epic":
            if overall_score >= 0.90:
                return (
                    "PASS",
                    "Epic demonstrates comprehensive quality across all stories",
                )
            elif overall_score >= 0.75:
                return (
                    "CONCERNS",
                    "Epic has acceptable quality but some areas need attention",
                )
            else:
                return "FAIL", "Epic quality is insufficient for integration"

        elif gate_type == "sprint":
            if overall_score >= 0.85:
                return "PASS", "Sprint delivers quality work with good team performance"
            elif overall_score >= 0.70:
                return (
                    "CONCERNS",
                    "Sprint acceptable but team should address quality issues",
                )
            else:
                return "FAIL", "Sprint quality is unacceptable and blocks progression"

        elif gate_type == "release":
            # Release gates have the highest bar - no compromises
            if overall_score >= 0.98:
                return (
                    "PASS",
                    "Release meets all quality requirements for production deployment",
                )
            elif overall_score >= 0.95:
                return (
                    "CONCERNS",
                    "Release has minor issues that should be documented and tracked",
                )
            else:
                return (
                    "FAIL",
                    "Release quality is insufficient for production deployment",
                )

        else:
            # Default to story thresholds for unknown gate types
            if overall_score >= 0.95:
                return "PASS", "Meets all quality criteria with excellent completion"
            elif overall_score >= 0.85:
                return (
                    "CONCERNS",
                    "Meets basic requirements but has minor quality issues",
                )
            else:
                return "FAIL", "Does not meet minimum quality standards"

    def validate_quality_gate(
        self, checklist_id: str, gate_type: str = "story"
    ) -> Dict[str, Any]:
        """Validate a quality gate using the appropriate checklist with enhanced reporting.

        Args:
            checklist_id: Checklist to use for validation
            gate_type: Type of gate ('story', 'epic', 'sprint')

        Returns:
            Gate validation results with comprehensive reporting
        """
        # Execute checklist
        execution_results = self.execute_checklist(checklist_id)

        # Add gate-specific information
        gate_results = {
            "gate_type": gate_type,
            "checklist_id": checklist_id,
            "timestamp": "2025-09-18T12:00:00Z",  # Would use datetime.now() in real implementation
            "execution_results": execution_results,
        }

        # Generate gate decision
        gate_results["decision"] = execution_results.get("gate_decision", "UNKNOWN")
        gate_results["confidence"] = self._calculate_confidence(gate_results)

        # Add enhanced reporting
        gate_results["assessment_report"] = self._generate_assessment_report(
            gate_results
        )
        gate_results["actionable_feedback"] = self._generate_actionable_feedback(
            gate_results
        )

        self.logger.info(
            f"Quality gate {gate_type} validation completed: {gate_results['decision']} "
            f"(confidence: {gate_results['confidence']:.1f})"
        )
        return gate_results

    def _generate_assessment_report(
        self, gate_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a comprehensive quality assessment report.

        Args:
            gate_results: Complete gate validation results

        Returns:
            Structured assessment report
        """
        execution_results = gate_results.get("execution_results", {})
        gate_type = gate_results.get("gate_type", "unknown")

        report = {
            "summary": {
                "gate_type": gate_type,
                "decision": gate_results.get("decision", "UNKNOWN"),
                "confidence_score": gate_results.get("confidence", 0.0),
                "overall_completion": execution_results.get("overall_score", 0),
                "artefact_type": execution_results.get("artefact_type", "unknown"),
                "acceptance_threshold": execution_results.get(
                    "acceptance_threshold", 0.8
                ),
                "assessment_timestamp": gate_results.get("timestamp"),
            },
            "detailed_findings": {
                "sections_analysis": self._analyze_sections_detailed(execution_results),
                "artefact_specific_findings": execution_results.get(
                    "artefact_specific_findings", []
                ),
                "critical_issues": self._identify_critical_issues_detailed(
                    execution_results
                ),
                "quality_indicators": self._calculate_quality_indicators(
                    execution_results
                ),
            },
            "recommendations": {
                "immediate_actions": self._generate_immediate_actions(gate_results),
                "improvement_suggestions": self._generate_improvement_suggestions(
                    execution_results
                ),
                "next_steps": self._generate_next_steps(gate_results),
            },
            "metadata": {
                "checklist_id": gate_results.get("checklist_id"),
                "validation_rules_applied": self._collect_validation_rules(
                    execution_results
                ),
                "processing_notes": self._generate_processing_notes(gate_results),
            },
        }

        return report

    def _analyze_sections_detailed(
        self, execution_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Provide detailed analysis of each section's performance."""
        sections_analysis = []
        sections = execution_results.get("sections", {})

        for section_name, section_data in sections.items():
            analysis = {
                "section_name": section_name,
                "completion_rate": 0.0,
                "total_items": section_data.get("total_items", 0),
                "completed_items": section_data.get("completed_items", 0),
                "failed_items": section_data.get("failed_items", []),
                "is_critical": section_data.get("is_critical", False),
                "artefact_validation": section_data.get("artefact_validation", {}),
                "performance_rating": "unknown",
                "key_insights": [],
            }

            # Calculate completion rate
            if analysis["total_items"] > 0:
                analysis["completion_rate"] = (
                    analysis["completed_items"] / analysis["total_items"]
                )

            # Determine performance rating
            if analysis["completion_rate"] >= 0.9:
                analysis["performance_rating"] = "excellent"
            elif analysis["completion_rate"] >= 0.7:
                analysis["performance_rating"] = "good"
            elif analysis["completion_rate"] >= 0.5:
                analysis["performance_rating"] = "needs_improvement"
            else:
                analysis["performance_rating"] = "critical_attention_required"

            # Generate key insights
            analysis["key_insights"] = self._generate_section_insights(analysis)

            sections_analysis.append(analysis)

        return sections_analysis

    def _generate_section_insights(self, section_analysis: Dict[str, Any]) -> List[str]:
        """Generate key insights for a section's performance."""
        insights = []

        completion_rate = section_analysis["completion_rate"]
        failed_items = section_analysis["failed_items"]
        is_critical = section_analysis["is_critical"]

        if completion_rate == 1.0:
            insights.append("Perfect completion - all requirements satisfied")
        elif completion_rate >= 0.8:
            insights.append("Strong performance with minor gaps")
        elif completion_rate >= 0.6:
            insights.append("Moderate performance - several items need attention")
        else:
            insights.append("Significant gaps requiring immediate focus")

        if failed_items:
            insights.append(f"{len(failed_items)} items failed validation")

        if is_critical and completion_rate < 0.9:
            insights.append("Critical section performance below acceptable threshold")

        artefact_validation = section_analysis.get("artefact_validation", {})
        if artefact_validation.get("specific_findings"):
            insights.append(
                (
                    f"{len(artefact_validation['specific_findings'])} "
                    "artefact-specific findings identified"
                )
            )

        return insights

    def _identify_critical_issues_detailed(
        self, execution_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify critical issues with detailed analysis."""
        critical_issues = []
        sections = execution_results.get("sections", {})

        for section_name, section_data in sections.items():
            failed_items = section_data.get("failed_items", [])
            is_critical = section_data.get("is_critical", False)

            for failed_item in failed_items:
                issue = {
                    "section": section_name,
                    "failed_item": failed_item,
                    "severity": "high" if is_critical else "medium",
                    "impact": "critical" if is_critical else "moderate",
                    "recommended_action": self._generate_issue_remediation(
                        failed_item, section_name
                    ),
                }
                critical_issues.append(issue)

        # Add artefact-specific critical issues
        artefact_findings = execution_results.get("artefact_specific_findings", [])
        for finding in artefact_findings:
            if finding.get("severity") == "high":
                critical_issues.append(
                    {
                        "section": finding.get("section", "artefact_validation"),
                        "failed_item": finding.get("finding", ""),
                        "severity": "high",
                        "impact": "artefact_compliance",
                        "recommended_action": finding.get(
                            "recommendation", "Review artefact compliance"
                        ),
                    }
                )

        return critical_issues

    def _generate_issue_remediation(self, failed_item: str, section_name: str) -> str:
        """Generate specific remediation actions for failed items."""
        item_lower = failed_item.lower()
        section_lower = section_name.lower()

        # Acceptance criteria issues
        if "acceptance" in section_lower and "criteria" in section_lower:
            if "measurable" in item_lower or "indicator" in item_lower:
                return (
                    "Add specific, measurable success indicators "
                    "(should, must, can, will, verify)"
                )
            return "Review and clarify acceptance criteria to ensure testability"

        # Testing issues
        if "testing" in section_lower or "test" in section_lower:
            if "type" in item_lower or "coverage" in item_lower:
                return "Specify test types needed (unit, integration, e2e, acceptance)"
            return (
                "Define comprehensive testing approach with clear coverage requirements"
            )

        # Security issues
        if "security" in section_lower:
            return (
                "Address specific security concerns "
                "(authentication, authorization, validation, etc.)"
            )

        # General remediation
        return "Review and enhance item to meet quality standards"

    def _calculate_quality_indicators(
        self, execution_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate comprehensive quality indicators."""
        sections = execution_results.get("sections", {})
        # artefact_type is not used in this method but kept for potential future use

        indicators = {
            "completion_distribution": {
                "excellent": 0,  # >= 90%
                "good": 0,  # 70-89%
                "fair": 0,  # 50-69%
                "poor": 0,  # < 50%
            },
            "critical_sections_status": {
                "total_critical": 0,
                "critical_passed": 0,
                "critical_failed": 0,
            },
            "artefact_compliance_score": 0.0,
            "validation_rules_coverage": 0,
            "overall_quality_score": execution_results.get("overall_score", 0),
        }

        # Analyze section completion distribution
        for section_data in sections.values():
            completion_rate = 0.0
            if section_data.get("total_items", 0) > 0:
                completion_rate = (
                    section_data.get("completed_items", 0) / section_data["total_items"]
                )

            if completion_rate >= 0.9:
                indicators["completion_distribution"]["excellent"] += 1
            elif completion_rate >= 0.7:
                indicators["completion_distribution"]["good"] += 1
            elif completion_rate >= 0.5:
                indicators["completion_distribution"]["fair"] += 1
            else:
                indicators["completion_distribution"]["poor"] += 1

            # Track critical sections
            if section_data.get("is_critical", False):
                indicators["critical_sections_status"]["total_critical"] += 1
                if completion_rate >= 0.8:  # Critical sections need higher threshold
                    indicators["critical_sections_status"]["critical_passed"] += 1
                else:
                    indicators["critical_sections_status"]["critical_failed"] += 1

        # Calculate artefact compliance score
        artefact_findings = execution_results.get("artefact_specific_findings", [])
        if artefact_findings:
            high_severity = sum(
                1 for f in artefact_findings if f.get("severity") == "high"
            )
            indicators["artefact_compliance_score"] = max(
                0, 1.0 - (high_severity * 0.2)
            )

        # Count validation rules applied
        validation_rules_count = 0
        for section_data in sections.values():
            artefact_validation = section_data.get("artefact_validation", {})
            validation_rules_count += len(
                artefact_validation.get("validation_rules_applied", [])
            )

        indicators["validation_rules_coverage"] = validation_rules_count

        return indicators

    def _generate_immediate_actions(
        self, gate_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate immediate actions required based on gate results."""
        actions = []
        decision = gate_results.get("decision", "UNKNOWN")

        if decision == "FAIL":
            actions.append(
                {
                    "action": "Address all critical issues before proceeding",
                    "priority": "immediate",
                    "reason": "Gate failed - blocking issues must be resolved",
                }
            )

        elif decision == "CONCERNS":
            actions.append(
                {
                    "action": "Review and document identified issues",
                    "priority": "high",
                    "reason": "Gate passed with concerns - issues should be tracked",
                }
            )

        # Add section-specific immediate actions
        execution_results = gate_results.get("execution_results", {})
        critical_issues = self._identify_critical_issues_detailed(execution_results)

        for issue in critical_issues[:3]:  # Top 3 critical issues
            actions.append(
                {
                    "action": f"Fix: {issue['failed_item'][:50]}...",
                    "priority": "high" if issue["severity"] == "high" else "medium",
                    "reason": f"Critical issue in {issue['section']}",
                }
            )

        return actions

    def _generate_improvement_suggestions(
        self, execution_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for quality improvements."""
        suggestions = []
        overall_score = execution_results.get("overall_score", 0)
        artefact_type = execution_results.get("artefact_type", "unknown")

        # General improvement suggestions based on score
        if overall_score < 0.7:
            suggestions.append(
                {
                    "area": "overall_quality",
                    "suggestion": "Implement comprehensive quality practices and training",
                    "impact": "high",
                    "effort": "high",
                }
            )

        elif overall_score < 0.85:
            suggestions.append(
                {
                    "area": "process_improvement",
                    "suggestion": "Enhance validation processes and checklists",
                    "impact": "medium",
                    "effort": "medium",
                }
            )

        # Artefact-specific suggestions
        if artefact_type == "story":
            suggestions.append(
                {
                    "area": "acceptance_criteria",
                    "suggestion": "Focus on measurable acceptance criteria with "
                    "clear success indicators",
                    "impact": "high",
                    "effort": "low",
                }
            )

        elif artefact_type == "architecture":
            suggestions.append(
                {
                    "area": "security_considerations",
                    "suggestion": "Enhance security validation and threat modeling",
                    "impact": "high",
                    "effort": "medium",
                }
            )

        # Section-specific suggestions
        sections = execution_results.get("sections", {})
        for section_name, section_data in sections.items():
            completion_rate = 0.0
            if section_data.get("total_items", 0) > 0:
                completion_rate = (
                    section_data.get("completed_items", 0) / section_data["total_items"]
                )

            if completion_rate < 0.8:
                suggestions.append(
                    {
                        "area": f"section_{section_name.lower().replace(' ', '_')}",
                        "suggestion": f"Improve {section_name} section completeness and quality",
                        "impact": "medium",
                        "effort": "medium",
                    }
                )

        return suggestions

    def _generate_next_steps(self, gate_results: Dict[str, Any]) -> List[str]:
        """Generate recommended next steps based on gate results."""
        next_steps = []
        decision = gate_results.get("decision", "UNKNOWN")

        if decision == "PASS":
            next_steps.append("Proceed to next workflow step or deployment")
            next_steps.append("Monitor for any issues in production")
            next_steps.append(
                "Consider implementing suggested improvements for future work"
            )

        elif decision == "CONCERNS":
            next_steps.append("Document and track identified issues")
            next_steps.append("Proceed with caution and monitoring")
            next_steps.append("Schedule follow-up review after implementation")

        elif decision == "FAIL":
            next_steps.append("Address all critical issues before proceeding")
            next_steps.append("Re-run quality gate validation after fixes")
            next_steps.append("Consider additional quality practices or reviews")

        # Add general next steps
        next_steps.append("Review assessment report for detailed findings")
        next_steps.append("Archive gate results for future reference")
        next_steps.append("Update team knowledge base with lessons learned")

        return next_steps

    def _collect_validation_rules(self, execution_results: Dict[str, Any]) -> List[str]:
        """Collect all validation rules that were applied."""
        rules_applied = set()

        sections = execution_results.get("sections", {})
        for section_data in sections.values():
            artefact_validation = section_data.get("artefact_validation", {})
            section_rules = artefact_validation.get("validation_rules_applied", [])
            rules_applied.update(section_rules)

        return sorted(list(rules_applied))

    def _generate_processing_notes(self, gate_results: Dict[str, Any]) -> List[str]:
        """Generate processing notes and metadata."""
        notes = []
        execution_results = gate_results.get("execution_results", {})

        # Add artefact type detection note
        artefact_type = execution_results.get("artefact_type", "unknown")
        if artefact_type != "unknown":
            notes.append(f"Artefact type detected: {artefact_type}")
        else:
            notes.append("Artefact type could not be automatically detected")

        # Add processing notes
        sections_count = len(execution_results.get("sections", {}))
        notes.append(f"Processed {sections_count} sections with validation rules")

        # Add confidence notes
        confidence = gate_results.get("confidence", 0)
        if confidence >= 0.9:
            notes.append("High confidence in gate decision")
        elif confidence >= 0.7:
            notes.append("Moderate confidence in gate decision")
        else:
            notes.append("Low confidence in gate decision - consider manual review")

        return notes

    def _generate_actionable_feedback(
        self, gate_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive actionable feedback for quality improvements."""
        feedback = {
            "executive_summary": self._generate_feedback_summary(gate_results),
            "priority_actions": self._generate_priority_actions(gate_results),
            "detailed_feedback": self._generate_detailed_feedback(gate_results),
            "improvement_roadmap": self._generate_improvement_roadmap(gate_results),
        }

        return feedback

    def _generate_feedback_summary(self, gate_results: Dict[str, Any]) -> str:
        """Generate a concise executive summary of the feedback."""
        decision = gate_results.get("decision", "UNKNOWN")
        confidence = gate_results.get("confidence", 0)
        execution_results = gate_results.get("execution_results", {})
        overall_score = execution_results.get("overall_score", 0)

        summary = f"Quality gate {decision} with {confidence:.1f} confidence. "
        summary += f"Overall completion: {overall_score:.1f}. "

        critical_issues = len(
            self._identify_critical_issues_detailed(execution_results)
        )
        if critical_issues > 0:
            summary += (
                f"{critical_issues} critical issues identified requiring attention."
            )

        return summary

    def _generate_priority_actions(
        self, gate_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate prioritized actions for immediate implementation."""
        actions = []
        decision = gate_results.get("decision", "UNKNOWN")
        execution_results = gate_results.get("execution_results", {})

        # Decision-based priority actions
        if decision == "FAIL":
            actions.append(
                {
                    "priority": 1,
                    "action": "STOP: Address all critical issues before proceeding",
                    "timeframe": "immediate",
                    "owner": "development_team",
                }
            )

        elif decision == "CONCERNS":
            actions.append(
                {
                    "priority": 1,
                    "action": "Document identified issues and create mitigation plan",
                    "timeframe": "within_24_hours",
                    "owner": "product_owner",
                }
            )

        # Section-specific priority actions
        sections = execution_results.get("sections", {})
        for section_name, section_data in sections.items():
            if section_data.get("is_critical", False):
                completion_rate = 0.0
                if section_data.get("total_items", 0) > 0:
                    completion_rate = (
                        section_data.get("completed_items", 0)
                        / section_data["total_items"]
                    )

                if completion_rate < 0.9:
                    actions.append(
                        {
                            "priority": 2,
                            "action": f"Improve {section_name} section quality and completeness",
                            "timeframe": "within_1_week",
                            "owner": "responsible_team",
                        }
                    )

        return actions

    def _generate_detailed_feedback(
        self, gate_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate detailed feedback for each aspect of the validation."""
        feedback = {}
        execution_results = gate_results.get("execution_results", {})

        # Section-by-section feedback
        sections = execution_results.get("sections", {})
        feedback["section_feedback"] = {}

        for section_name, section_data in sections.items():
            section_feedback = {
                "performance_rating": "unknown",
                "strengths": [],
                "weaknesses": [],
                "recommendations": [],
            }

            # Calculate performance
            completion_rate = 0.0
            if section_data.get("total_items", 0) > 0:
                completion_rate = (
                    section_data.get("completed_items", 0) / section_data["total_items"]
                )

            if completion_rate >= 0.9:
                section_feedback["performance_rating"] = "excellent"
                section_feedback["strengths"].append("High completion rate")
            elif completion_rate >= 0.7:
                section_feedback["performance_rating"] = "good"
                section_feedback["strengths"].append("Good overall completion")
                section_feedback["weaknesses"].append("Some items need attention")
            else:
                section_feedback["performance_rating"] = "needs_improvement"
                section_feedback["weaknesses"].append("Significant completion gaps")

            # Add artefact-specific feedback
            artefact_validation = section_data.get("artefact_validation", {})
            specific_findings = artefact_validation.get("specific_findings", [])

            for finding in specific_findings:
                section_feedback["weaknesses"].append(finding)
                section_feedback["recommendations"].append(
                    self._generate_finding_recommendation(
                        finding, execution_results.get("artefact_type", "unknown")
                    )
                )

            feedback["section_feedback"][section_name] = section_feedback

        return feedback

    def _generate_improvement_roadmap(
        self, gate_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate a roadmap for quality improvements."""
        roadmap = []
        execution_results = gate_results.get("execution_results", {})
        artefact_type = execution_results.get("artefact_type", "unknown")

        # Short-term improvements (next sprint)
        roadmap.append(
            {
                "phase": "immediate_next_sprint",
                "focus": "Address critical issues and immediate gaps",
                "actions": [
                    "Fix all critical validation failures",
                    "Improve acceptance criteria clarity",
                    "Enhance testing specifications",
                ],
                "expected_impact": "Pass quality gates consistently",
            }
        )

        # Medium-term improvements (next 2-3 sprints)
        roadmap.append(
            {
                "phase": "medium_term_2_3_sprints",
                "focus": "Implement quality practices and automation",
                "actions": [
                    f"Develop {artefact_type}-specific validation templates",
                    "Implement automated quality checks",
                    "Train team on quality standards",
                ],
                "expected_impact": "Reduce review cycles and improve consistency",
            }
        )

        # Long-term improvements (next month+)
        roadmap.append(
            {
                "phase": "long_term_monthly",
                "focus": "Continuous quality improvement",
                "actions": [
                    "Regular quality metrics review",
                    "Process optimization based on data",
                    "Advanced quality tooling adoption",
                ],
                "expected_impact": "Industry-leading quality standards",
            }
        )

        return roadmap

    def _calculate_confidence(self, gate_results: Dict[str, Any]) -> float:
        """Calculate confidence score for gate decision (0.0 to 1.0).

        Args:
            gate_results: Gate validation results

        Returns:
            Confidence score between 0.0 and 1.0
        """
        execution = gate_results.get("execution_results", {})
        score = execution.get("overall_score", 0)

        # Base confidence on score
        base_confidence = score

        # Adjust based on data completeness
        sections = execution.get("sections", {})
        if not sections:
            base_confidence *= 0.8  # Reduce confidence if no section data

        # Adjust based on artefact type detection
        artefact_type = execution.get("artefact_type", "unknown")
        if artefact_type == "unknown":
            base_confidence *= 0.9  # Slight reduction for unknown artefact types

        return min(max(base_confidence, 0.0), 1.0)

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
