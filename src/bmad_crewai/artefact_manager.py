"""Artefact writing and management functionality."""

import logging
from enum import Enum
from typing import Any, Dict, Optional

from .artefact_writer import BMADArtefactWriter

logger = logging.getLogger(__name__)


class ArtefactType(Enum):
    """Enumeration of supported BMAD artefact types."""

    PRD = "prd"
    ARCHITECTURE = "architecture"
    STORIES = "stories"
    QA_ASSESSMENTS = "qa_assessments"
    QA_GATES = "qa_gates"
    EPICS = "epics"
    TEMPLATES = "templates"


class BmadArtefactGenerator:
    """Comprehensive artefact generation system with type detection and routing.

    This class manages the complete artefact generation pipeline, including:
    - Artefact type detection from content or context
    - Template loading and content processing
    - Quality validation during generation
    - Dependency management and cross-reference resolution
    """

    def __init__(self, artefact_writer: Optional[BMADArtefactWriter] = None):
        """Initialize the artefact generator.

        Args:
            artefact_writer: Optional BMADArtefactWriter instance
        """
        self.artefact_writer = artefact_writer or BMADArtefactWriter()
        self.logger = logging.getLogger(__name__)

    def detect_artefact_type(
        self, content: str, context: Optional[Dict[str, Any]] = None
    ) -> ArtefactType:
        """Detect artefact type from content and context.

        Args:
            content: Artefact content to analyze
            context: Additional context information

        Returns:
            ArtefactType: Detected artefact type
        """
        content_lower = content.lower()

        # Check for specific artefact markers
        if any(
            marker in content_lower
            for marker in [
                "# prd",
                "# product requirements",
                "product requirements document",
            ]
        ):
            return ArtefactType.PRD
        elif any(
            marker in content_lower
            for marker in [
                "architecture",
                "# system architecture",
                "technical architecture",
            ]
        ):
            return ArtefactType.ARCHITECTURE
        elif any(
            marker in content_lower
            for marker in ["# story", "as a", "i want", "acceptance criteria"]
        ):
            return ArtefactType.STORIES
        elif any(
            marker in content_lower for marker in ["quality gate", "qa gate", "gate:"]
        ):
            return ArtefactType.QA_GATES
        elif any(
            marker in content_lower
            for marker in ["assessment", "risk profile", "traceability"]
        ):
            return ArtefactType.QA_ASSESSMENTS
        elif any(marker in content_lower for marker in ["# epic", "epic goal"]):
            return ArtefactType.EPICS
        elif any(marker in content_lower for marker in ["template", "{{", "}}"]):
            return ArtefactType.TEMPLATES

        # Fallback based on context
        if context:
            context_type = context.get("type", "").lower()
            if context_type in [
                "prd",
                "architecture",
                "stories",
                "qa_gates",
                "qa_assessments",
                "epics",
                "templates",
            ]:
                return ArtefactType(context_type)

        # Default to stories if unclear
        self.logger.warning("Could not detect artefact type, defaulting to STORIES")
        return ArtefactType.STORIES

    def generate_artefact(
        self, artefact_type: ArtefactType, content: str, **kwargs
    ) -> bool:
        """Generate and write artefact using the artefact generation pipeline.

        Args:
            artefact_type: Type of artefact to generate
            content: Artefact content
            **kwargs: Additional parameters for artefact generation

        Returns:
            bool: True if generation successful
        """
        try:
            self.logger.info(f"Generating artefact of type: {artefact_type.value}")

            # Validate content before processing
            if not self._validate_content_quality(artefact_type, content):
                self.logger.error(
                    f"Content quality validation failed for {artefact_type.value}"
                )
                return False

            # Process content based on artefact type
            processed_content = self._process_content(artefact_type, content, **kwargs)

            # Generate cross-references if needed
            processed_content = self._add_cross_references(
                artefact_type, processed_content, **kwargs
            )

            # Write artefact using writer
            success = self._write_artefact(artefact_type, processed_content, **kwargs)

            if success:
                self.logger.info(
                    f"Successfully generated artefact: {artefact_type.value}"
                )
            else:
                self.logger.error(f"Failed to write artefact: {artefact_type.value}")

            return success

        except Exception as e:
            self.logger.error(
                f"Artefact generation failed for {artefact_type.value}: {e}"
            )
            return False

    def _validate_content_quality(
        self, artefact_type: ArtefactType, content: str
    ) -> bool:
        """Validate content quality before generation.

        Args:
            artefact_type: Type of artefact
            content: Content to validate

        Returns:
            bool: True if content passes quality checks
        """
        if not content or not content.strip():
            self.logger.error("Empty content provided")
            return False

        # Type-specific validation
        if artefact_type == ArtefactType.PRD:
            if len(content) < 100:  # Basic length check
                self.logger.warning("PRD content appears too short")
        elif artefact_type == ArtefactType.STORIES:
            if "## acceptance criteria" not in content.lower():
                self.logger.warning("Story missing acceptance criteria section")

        return True  # Pass for now, could be more strict

    def _process_content(
        self, artefact_type: ArtefactType, content: str, **kwargs
    ) -> str:
        """Process content based on artefact type requirements.

        Args:
            artefact_type: Type of artefact
            content: Raw content
            **kwargs: Processing parameters

        Returns:
            str: Processed content
        """
        # Add standard headers/footers based on type
        processed = content

        if artefact_type == ArtefactType.STORIES:
            # Ensure stories have proper status
            if "## Status:" not in processed:
                processed = "## Status: Draft\n\n" + processed
        elif artefact_type == ArtefactType.QA_GATES:
            # Ensure gates have schema
            if "schema:" not in processed:
                processed = "schema: 1\n" + processed

        return processed

    def _add_cross_references(
        self, artefact_type: ArtefactType, content: str, **kwargs
    ) -> str:
        """Add cross-references to related artefacts.

        Args:
            artefact_type: Type of artefact
            content: Content to enhance
            **kwargs: Reference parameters

        Returns:
            str: Content with cross-references
        """
        # This could be enhanced to automatically add links to related artefacts
        # For now, return content as-is
        return content

    def _write_artefact(
        self, artefact_type: ArtefactType, content: str, **kwargs
    ) -> bool:
        """Write artefact using the artefact writer.

        Args:
            artefact_type: Type of artefact
            content: Processed content
            **kwargs: Writing parameters

        Returns:
            bool: True if writing successful
        """
        try:
            # Map enum to string for writer compatibility
            artefact_type_str = artefact_type.value

            return self.artefact_writer.write_artefact(
                artefact_type_str, content, **kwargs
            )

        except Exception as e:
            self.logger.error(f"Failed to write artefact {artefact_type.value}: {e}")
            return False


class ArtefactManager:
    """Manager for writing artefacts to BMAD folder structure with comprehensive generation support."""

    def __init__(self):
        self.artefact_writer = BMADArtefactWriter()
        self.artefact_generator = BmadArtefactGenerator(self.artefact_writer)
        self.logger = logging.getLogger(__name__)

    def write_artefact(self, artefact_type: str, content: str, **kwargs) -> bool:
        """Write artefact to BMAD folder structure using FOLDER_MAPPING.

        Args:
            artefact_type: Type of artefact ('prd', 'stories', 'qa_assessments',
                           'qa_gates', 'epics')
            content: Artefact content
            **kwargs: Additional parameters for specific artefact types

        Returns:
            bool: True if successful
        """
        try:
            # Map legacy artefact types to new FOLDER_MAPPING keys
            type_mapping = {
                "prd": "prd",
                "story": "stories",
                "gate": "qa_gates",
                "assessment": "qa_assessments",
                "epic": "epics",
            }

            mapped_type = type_mapping.get(artefact_type, artefact_type)

            return self.artefact_writer.write_artefact(mapped_type, content, **kwargs)

        except Exception as e:
            self.logger.error(f"Failed to write artefact {artefact_type}: {e}")
            return False

    def generate_comprehensive_artefact(
        self,
        content: str,
        artefact_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> bool:
        """Generate artefact using comprehensive artefact generation pipeline.

        Args:
            content: Artefact content to generate
            artefact_type: Optional artefact type override
            context: Additional context for generation
            **kwargs: Additional parameters for generation

        Returns:
            bool: True if generation successful
        """
        try:
            # Detect artefact type if not provided
            if artefact_type:
                detected_type = ArtefactType(artefact_type)
            else:
                detected_type = self.artefact_generator.detect_artefact_type(
                    content, context
                )

            # Generate artefact using comprehensive pipeline
            return self.artefact_generator.generate_artefact(
                detected_type, content, **kwargs
            )

        except Exception as e:
            self.logger.error(f"Comprehensive artefact generation failed: {e}")
            return False

    def validate_artefact_consistency(
        self, artefact_type: str, content: str
    ) -> Dict[str, Any]:
        """Validate artefact consistency and cross-references.

        Args:
            artefact_type: Type of artefact to validate
            content: Content to validate

        Returns:
            Dict with validation results
        """
        results = {
            "consistent": True,
            "issues": [],
            "cross_references": [],
            "recommendations": [],
        }

        try:
            # Basic structure validation
            if artefact_type == "stories":
                if "## Acceptance Criteria" not in content:
                    results["issues"].append("Missing Acceptance Criteria section")
                    results["consistent"] = False
                if "## Status:" not in content:
                    results["issues"].append("Missing Status section")
                    results["consistent"] = False

            elif artefact_type == "qa_gates":
                if "gate:" not in content.lower():
                    results["issues"].append("Missing gate decision")
                    results["consistent"] = False

            # Cross-reference validation (basic implementation)
            if artefact_type == "stories":
                # Check for references to other artefacts
                if "docs/architecture/" in content:
                    results["cross_references"].append(
                        "References architecture documents"
                    )
                if "docs/qa/" in content:
                    results["cross_references"].append("References QA artefacts")

        except Exception as e:
            results["consistent"] = False
            results["issues"].append(f"Validation error: {e}")

        return results

    def test_artefact_generation(self) -> Dict[str, Any]:
        """Test artefact generation functionality.

        Returns:
            Dict with artefact generation test results
        """
        try:
            results = self.artefact_writer.test_artefact_writing()
            self.logger.info("Artefact generation test completed")
            return results
        except Exception as e:
            self.logger.error(f"Artefact generation test failed: {e}")
            return {"error": str(e)}
