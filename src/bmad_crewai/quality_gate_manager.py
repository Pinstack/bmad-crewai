"""Quality gate and checklist management functionality."""

import logging
from typing import Any, Dict, Optional

from .checklist_executor import ChecklistExecutor

logger = logging.getLogger(__name__)


class QualityGateManager:
    """Manager for quality gates and checklist execution."""

    def __init__(self):
        self.checklist_executor = ChecklistExecutor()
        self.logger = logging.getLogger(__name__)

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
        try:
            results = self.checklist_executor.validate_quality_gate(
                checklist_id, gate_type
            )
            self.logger.info(
                f"Quality gate {gate_type} validated: "
                f"{results.get('decision', 'UNKNOWN')}"
            )
            return results
        except Exception as e:
            self.logger.error(f"Gate validation failed: {e}")
            return {"error": str(e)}

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
