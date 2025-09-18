"""Artefact writing and management functionality."""

import logging
from typing import Any, Dict

from .artefact_writer import BMADArtefactWriter

logger = logging.getLogger(__name__)


class ArtefactManager:
    """Manager for writing artefacts to BMAD folder structure."""

    def __init__(self):
        self.artefact_writer = BMADArtefactWriter()
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
