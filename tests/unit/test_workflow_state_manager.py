"""
Unit tests for WorkflowStateManager.

Tests cover:
- State persistence and recovery
- Agent handoff tracking and dependency management
- Progress monitoring and status updates
- Workflow interruption and recovery scenarios
- Concurrent operations and state synchronization
- State validation and corruption handling
"""

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.bmad_crewai.workflow_state_manager import WorkflowStateManager


class TestWorkflowStateManager(unittest.TestCase):
    """Test cases for WorkflowStateManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_manager = WorkflowStateManager(
            logger=MagicMock(),
            storage_dir=self.temp_dir
        )

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove all files in temp directory
        for file_path in Path(self.temp_dir).glob("*"):
            if file_path.is_file():
                file_path.unlink()
        os.rmdir(self.temp_dir)

    def test_initialization(self):
        """Test WorkflowStateManager initialization."""
        self.assertIsNotNone(self.state_manager.logger)
        self.assertEqual(str(self.state_manager.storage_dir), self.temp_dir)
        self.assertTrue(self.state_manager.storage_dir.exists())

    def test_persist_state_success(self):
        """Test successful state persistence."""
        workflow_id = "test_workflow_1"
        state_dict = {
            "status": "running",
            "current_step": "task_1",
            "steps_completed": [0],
            "total_steps": 3
        }

        result = self.state_manager.persist_state(workflow_id, state_dict)
        self.assertTrue(result)

        # Verify file was created
        state_file = self.state_manager.storage_dir / f"{workflow_id}.json"
        self.assertTrue(state_file.exists())

        # Verify content
        with open(state_file, 'r') as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data["status"], "running")
        self.assertEqual(saved_data["current_step"], "task_1")
        self.assertIn("_metadata", saved_data)
        self.assertEqual(saved_data["_metadata"]["workflow_id"], workflow_id)

    def test_persist_state_validation_failure(self):
        """Test state persistence with invalid state structure."""
        workflow_id = "test_workflow_2"
        invalid_state = {}  # Missing required fields

        result = self.state_manager.persist_state(workflow_id, invalid_state)
        self.assertFalse(result)

    def test_recover_state_success(self):
        """Test successful state recovery."""
        workflow_id = "test_workflow_3"
        original_state = {
            "status": "completed",
            "current_step": "task_final",
            "steps_completed": [0, 1, 2],
            "total_steps": 3,
            "custom_data": "test_value"
        }

        # First persist the state
        self.state_manager.persist_state(workflow_id, original_state)

        # Now recover it
        recovered_state = self.state_manager.recover_state(workflow_id)

        self.assertIsNotNone(recovered_state)
        self.assertEqual(recovered_state["status"], "completed")
        self.assertEqual(recovered_state["current_step"], "task_final")
        self.assertEqual(recovered_state["custom_data"], "test_value")
        self.assertIn("_metadata", recovered_state)

    def test_recover_state_not_found(self):
        """Test state recovery for non-existent workflow."""
        recovered_state = self.state_manager.recover_state("non_existent_workflow")
        self.assertIsNone(recovered_state)

    def test_recover_state_corrupted_file(self):
        """Test recovery from corrupted state file."""
        workflow_id = "corrupted_workflow"

        # Create corrupted JSON file
        state_file = self.state_manager.storage_dir / f"{workflow_id}.json"
        with open(state_file, 'w') as f:
            f.write("{ invalid json content }")

        recovered_state = self.state_manager.recover_state(workflow_id)

        # Should return minimal recovery state
        self.assertIsNotNone(recovered_state)
        self.assertEqual(recovered_state["status"], "interrupted")
        self.assertIn("recovered", recovered_state.get("_metadata", {}))

    def test_track_agent_handoff_success(self):
        """Test successful agent handoff tracking."""
        workflow_id = "handoff_test_workflow"
        initial_state = {
            "status": "running",
            "current_step": "task_1",
            "steps_completed": [],
            "total_steps": 2
        }

        # Initialize workflow state
        self.state_manager.persist_state(workflow_id, initial_state)

        # Track handoff
        result = self.state_manager.track_agent_handoff(
            workflow_id=workflow_id,
            from_agent="architect",
            to_agent="dev-agent",
            handoff_data={"artifacts": ["design_docs"], "notes": "Ready for implementation"}
        )

        self.assertTrue(result)

        # Verify handoff was recorded
        state = self.state_manager.recover_state(workflow_id)
        self.assertIsNotNone(state)
        self.assertIn("agent_handoffs", state)
        self.assertEqual(len(state["agent_handoffs"]), 1)

        handoff = state["agent_handoffs"][0]
        self.assertEqual(handoff["from_agent"], "architect")
        self.assertEqual(handoff["to_agent"], "dev-agent")
        self.assertIn("data", handoff)
        self.assertEqual(handoff["data"]["artifacts"], ["design_docs"])

        # Verify dependencies
        self.assertIn("agent_dependencies", state)
        self.assertIn("architect", state["agent_dependencies"])
        self.assertIn("dev-agent", state["agent_dependencies"]["architect"])

    def test_track_agent_handoff_nonexistent_workflow(self):
        """Test agent handoff tracking for non-existent workflow."""
        result = self.state_manager.track_agent_handoff(
            workflow_id="nonexistent",
            from_agent="architect",
            to_agent="dev-agent"
        )
        self.assertFalse(result)

    def test_get_workflow_progress(self):
        """Test workflow progress retrieval."""
        workflow_id = "progress_test_workflow"
        state_dict = {
            "status": "running",
            "current_step": "task_2",
            "steps_completed": [0, 1],
            "total_steps": 5,
            "progress": {
                "completed": 2,
                "total": 5,
                "percentage": 40.0
            }
        }

        self.state_manager.persist_state(workflow_id, state_dict)

        progress = self.state_manager.get_workflow_progress(workflow_id)

        self.assertIsNotNone(progress)
        self.assertEqual(progress["status"], "running")
        self.assertEqual(progress["current_step"], "task_2")
        self.assertEqual(progress["steps_completed"], 2)
        self.assertEqual(progress["total_steps"], 5)
        self.assertEqual(progress["percentage"], 40.0)
        self.assertEqual(progress["agent_handoffs"], 0)

    def test_get_workflow_progress_with_handoffs_and_timeline(self):
        """Test workflow progress with handoffs and timeline."""
        workflow_id = "complex_progress_workflow"
        state_dict = {
            "status": "running",
            "current_step": "task_3",
            "steps_completed": [0, 1, 2],
            "total_steps": 4,
            "agent_handoffs": [
                {
                    "from_agent": "pm",
                    "to_agent": "architect",
                    "timestamp": "2025-01-01T10:00:00",
                    "data": {}
                },
                {
                    "from_agent": "architect",
                    "to_agent": "dev-agent",
                    "timestamp": "2025-01-01T11:00:00",
                    "data": {}
                }
            ],
            "execution_timeline": [
                {"type": "initialization", "timestamp": "2025-01-01T09:00:00"},
                {"type": "handoff", "timestamp": "2025-01-01T10:00:00"},
                {"type": "handoff", "timestamp": "2025-01-01T11:00:00"}
            ]
        }

        self.state_manager.persist_state(workflow_id, state_dict)

        progress = self.state_manager.get_workflow_progress(workflow_id)

        self.assertIsNotNone(progress)
        self.assertEqual(progress["agent_handoffs"], 2)
        self.assertEqual(progress["execution_timeline_entries"], 3)
        self.assertIn("recent_activities", progress)
        self.assertEqual(len(progress["recent_activities"]), 3)

    def test_validate_agent_handoff_success(self):
        """Test successful agent handoff validation."""
        workflow_id = "validation_test_workflow"
        state_dict = {
            "status": "running",
            "current_step": "task_1",
            "agent_handoffs": []
        }

        self.state_manager.persist_state(workflow_id, state_dict)

        validation = self.state_manager.validate_agent_handoff(
            workflow_id=workflow_id,
            from_agent="architect",
            to_agent="dev-agent"
        )

        self.assertTrue(validation["is_valid"])
        self.assertEqual(len(validation["warnings"]), 0)
        self.assertEqual(len(validation["errors"]), 0)

    def test_validate_agent_handoff_circular_dependency(self):
        """Test agent handoff validation with circular dependency."""
        workflow_id = "circular_test_workflow"
        state_dict = {
            "status": "running",
            "agent_dependencies": {
                "dev-agent": ["architect"]  # architect already depends on dev-agent
            }
        }

        self.state_manager.persist_state(workflow_id, state_dict)

        validation = self.state_manager.validate_agent_handoff(
            workflow_id=workflow_id,
            from_agent="architect",
            to_agent="dev-agent"
        )

        self.assertFalse(validation["is_valid"])
        self.assertIn("Circular dependency detected", validation["errors"][0])

    def test_validate_agent_handoff_workflow_not_running(self):
        """Test agent handoff validation when workflow is not in running state."""
        workflow_id = "paused_workflow"
        state_dict = {
            "status": "paused",
            "current_step": "task_1"
        }

        self.state_manager.persist_state(workflow_id, state_dict)

        validation = self.state_manager.validate_agent_handoff(
            workflow_id=workflow_id,
            from_agent="architect",
            to_agent="dev-agent"
        )

        self.assertTrue(validation["is_valid"])  # Still valid, just warnings
        self.assertIn("may not be expected", validation["warnings"][0])

    def test_recover_from_agent_failure(self):
        """Test recovery from agent failure."""
        workflow_id = "failure_recovery_test"
        state_dict = {
            "status": "running",
            "current_step": "task_2",
            "agent_handoffs": []
        }

        self.state_manager.persist_state(workflow_id, state_dict)

        recovery_result = self.state_manager.recover_from_agent_failure(
            workflow_id=workflow_id,
            failed_agent="dev-agent"
        )

        self.assertIsNotNone(recovery_result)
        self.assertEqual(recovery_result["can_resume"], True)
        self.assertIn("recovery_state", recovery_result)
        self.assertIn("options", recovery_result)

        # Check that workflow was marked as interrupted
        updated_state = self.state_manager.recover_state(workflow_id)
        self.assertEqual(updated_state["status"], "interrupted")
        self.assertEqual(updated_state["failure_agent"], "dev-agent")
        self.assertIn("recovery_options", updated_state)

    def test_mark_workflow_interrupted(self):
        """Test marking workflow as interrupted."""
        workflow_id = "interrupt_test_workflow"
        state_dict = {
            "status": "running",
            "current_step": "task_1"
        }

        self.state_manager.persist_state(workflow_id, state_dict)

        result = self.state_manager.mark_workflow_interrupted(
            workflow_id=workflow_id,
            reason="user_request"
        )

        self.assertTrue(result)

        updated_state = self.state_manager.recover_state(workflow_id)
        self.assertEqual(updated_state["status"], "interrupted")
        self.assertEqual(updated_state["interruption_reason"], "user_request")
        self.assertIn("interruption_time", updated_state)

    def test_list_active_workflows(self):
        """Test listing active workflows."""
        # Create multiple workflow states
        workflows_data = [
            ("active_workflow_1", {"status": "running", "current_step": "task_1"}),
            ("active_workflow_2", {"status": "initialized", "current_step": "setup"}),
            ("completed_workflow", {"status": "completed", "current_step": "final"}),
            ("failed_workflow", {"status": "failed", "current_step": "error"})
        ]

        for workflow_id, state_dict in workflows_data:
            self.state_manager.persist_state(workflow_id, state_dict)

        active_workflows = self.state_manager.list_active_workflows()

        # Should include running and initialized, but not completed/failed
        self.assertIn("active_workflow_1", active_workflows)
        self.assertIn("active_workflow_2", active_workflows)
        self.assertNotIn("completed_workflow", active_workflows)
        self.assertNotIn("failed_workflow", active_workflows)

    def test_cleanup_workflow_state(self):
        """Test workflow state cleanup."""
        workflow_id = "cleanup_test_workflow"
        state_dict = {"status": "completed", "current_step": "final"}

        # Create state file
        self.state_manager.persist_state(workflow_id, state_dict)

        # Verify file exists
        state_file = self.state_manager.storage_dir / f"{workflow_id}.json"
        self.assertTrue(state_file.exists())

        # Cleanup
        result = self.state_manager.cleanup_workflow_state(workflow_id)
        self.assertTrue(result)

        # Verify file is gone
        self.assertFalse(state_file.exists())

        # Test cleanup of non-existent workflow
        result = self.state_manager.cleanup_workflow_state("nonexistent")
        self.assertFalse(result)

    def test_validate_state_integrity_valid(self):
        """Test state integrity validation for valid state."""
        workflow_id = "integrity_test_workflow"
        valid_state = {
            "status": "running",
            "current_step": "task_1",
            "steps_completed": [0],
            "_metadata": {
                "workflow_id": workflow_id,
                "timestamp": "2025-01-01T10:00:00",
                "version": "1.0"
            }
        }

        self.state_manager.persist_state(workflow_id, valid_state)

        integrity = self.state_manager.validate_state_integrity(workflow_id)

        self.assertTrue(integrity["is_valid"])
        self.assertEqual(len(integrity["issues"]), 0)

    def test_validate_state_integrity_issues(self):
        """Test state integrity validation with issues."""
        workflow_id = "integrity_issues_workflow"
        problematic_state = {
            "status": "completed",
            "current_step": "task_1",
            "steps_completed": [],  # Completed but no steps completed
            "_metadata": {
                "workflow_id": workflow_id,
                "timestamp": "2025-01-01T10:00:00",
                "version": "1.0"
            }
        }

        self.state_manager.persist_state(workflow_id, problematic_state)

        integrity = self.state_manager.validate_state_integrity(workflow_id)

        self.assertTrue(integrity["is_valid"])  # No blocking issues
        self.assertGreater(len(integrity["issues"]), 0)

    def test_concurrent_operations(self):
        """Test concurrent workflow operations."""
        workflow_id = "concurrent_test_workflow"
        initial_state = {
            "status": "running",
            "current_step": "task_1",
            "steps_completed": [],
            "concurrent_access_count": 0
        }

        self.state_manager.persist_state(workflow_id, initial_state)

        results = []
        errors = []

        def concurrent_operation(operation_id: int):
            """Simulate concurrent operation."""
            try:
                # Read state
                state = self.state_manager.recover_state(workflow_id)
                if state:
                    # Modify state
                    state["concurrent_access_count"] = state.get("concurrent_access_count", 0) + 1
                    # Write state back
                    success = self.state_manager.persist_state(workflow_id, state)
                    results.append((operation_id, success))
                else:
                    results.append((operation_id, False))
            except Exception as e:
                errors.append((operation_id, str(e)))

        # Run concurrent operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations completed
        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 0)

        # Check final state
        final_state = self.state_manager.recover_state(workflow_id)
        self.assertIsNotNone(final_state)
        # The count should be exactly 5 due to thread safety
        self.assertEqual(final_state.get("concurrent_access_count"), 5)

    def test_state_corruption_backup(self):
        """Test that corrupted states are backed up."""
        workflow_id = "corruption_backup_test"
        original_state = {
            "status": "running",
            "current_step": "task_1",
            "steps_completed": [0]
        }

        # Persist original state
        self.state_manager.persist_state(workflow_id, original_state)

        # Manually corrupt the file
        state_file = self.state_manager.storage_dir / f"{workflow_id}.json"
        with open(state_file, 'w') as f:
            f.write("corrupted json content")

        # Attempt to recover (should create backup and return minimal state)
        recovered = self.state_manager.recover_state(workflow_id)

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered["status"], "interrupted")

        # Check that backup was created
        backup_files = list(self.state_manager.storage_dir.glob(f"{workflow_id}_corrupted_*.json"))
        self.assertEqual(len(backup_files), 1)


if __name__ == '__main__':
    unittest.main()
