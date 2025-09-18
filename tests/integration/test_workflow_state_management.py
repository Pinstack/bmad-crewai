"""
Integration tests for Workflow State Management.

Tests end-to-end workflow execution with state management, recovery, and concurrent operations.
"""

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from src.bmad_crewai.crewai_engine import BmadWorkflowEngine
from src.bmad_crewai.workflow_state_manager import WorkflowStateManager


class TestWorkflowStateManagementIntegration(unittest.TestCase):
    """Integration test suite for workflow state management."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_manager = WorkflowStateManager(
            logger=MagicMock(), storage_dir=self.temp_dir
        )

        # Create workflow engine with state manager
        self.workflow_engine = BmadWorkflowEngine(
            crew=None,  # Will be mocked
            state_manager=self.state_manager,
            logger=MagicMock(),
        )

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove all files in temp directory
        for file_path in Path(self.temp_dir).glob("*"):
            if file_path.is_file():
                file_path.unlink()
        Path(self.temp_dir).rmdir()

    @patch("src.bmad_crewai.crewai_engine.Crew")
    def test_end_to_end_workflow_execution_with_state_management(self, mock_crew_class):
        """Test complete workflow execution with state checkpoints and recovery."""
        # Arrange
        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew

        workflow_template = {
            "name": "test-workflow",
            "tasks": [
                {
                    "description": "Task 1: Initialize project",
                    "expected_output": "Project initialized",
                    "agent": "scrum-master",
                },
                {
                    "description": "Task 2: Create requirements",
                    "expected_output": "Requirements document",
                    "agent": "product-manager",
                },
                {
                    "description": "Task 3: Design architecture",
                    "expected_output": "Architecture design",
                    "agent": "architect",
                },
            ],
        }

        # Act
        result = self.workflow_engine.execute_workflow(
            workflow_template, "integration_test_workflow"
        )

        # Assert
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["task_results"]), 3)
        self.assertIn("workflow_id", result)

        # Verify state persistence
        workflow_id = result["workflow_id"]
        final_state = self.state_manager.recover_state(workflow_id)

        self.assertIsNotNone(final_state)
        self.assertEqual(final_state["status"], "completed")
        self.assertEqual(len(final_state["steps_completed"]), 3)
        self.assertEqual(final_state["total_steps"], 3)

        # Verify checkpoints were created
        self.assertIn("checkpoints", final_state)
        self.assertGreaterEqual(
            len(final_state["checkpoints"]), 3
        )  # At least one per task

        # Verify timeline
        self.assertIn("execution_timeline", final_state)
        timeline_entries = final_state["execution_timeline"]
        self.assertGreaterEqual(len(timeline_entries), 4)  # init + 3 tasks

    @patch("src.bmad_crewai.crewai_engine.Crew")
    def test_workflow_execution_with_agent_handoff_tracking(self, mock_crew_class):
        """Test workflow execution with agent handoff tracking."""
        # Arrange
        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew

        workflow_template = {
            "name": "handoff-test-workflow",
            "tasks": [
                {
                    "description": "Define requirements",
                    "expected_output": "Requirements defined",
                    "agent": "product-manager",
                },
                {
                    "description": "Design solution",
                    "expected_output": "Solution designed",
                    "agent": "architect",
                },
                {
                    "description": "Implement solution",
                    "expected_output": "Solution implemented",
                    "agent": "dev-agent",
                },
            ],
        }

        # Act
        result = self.workflow_engine.execute_workflow(
            workflow_template, "handoff_test_workflow"
        )

        # Assert successful execution
        self.assertEqual(result["status"], "success")

        # Verify handoff tracking
        workflow_id = result["workflow_id"]
        final_state = self.state_manager.recover_state(workflow_id)

        self.assertIn("agent_handoffs", final_state)
        handoffs = final_state["agent_handoffs"]

        # Should have 2 handoffs (between tasks)
        self.assertEqual(len(handoffs), 2)

        # Verify handoff sequence
        self.assertEqual(handoffs[0]["from_agent"], "product-manager")
        self.assertEqual(handoffs[0]["to_agent"], "architect")

        self.assertEqual(handoffs[1]["from_agent"], "architect")
        self.assertEqual(handoffs[1]["to_agent"], "dev-agent")

        # Verify dependencies
        self.assertIn("agent_dependencies", final_state)
        deps = final_state["agent_dependencies"]

        self.assertIn("product-manager", deps)
        self.assertIn("architect", deps["product-manager"])
        self.assertIn("architect", deps)
        self.assertIn("dev-agent", deps["architect"])

    @patch("src.bmad_crewai.crewai_engine.Crew")
    def test_workflow_interruption_and_recovery(self, mock_crew_class):
        """Test workflow interruption and recovery from checkpoint."""
        # Arrange
        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew

        workflow_template = {
            "name": "interruption-test-workflow",
            "tasks": [
                {
                    "description": "Task 1",
                    "expected_output": "Task 1 complete",
                    "agent": "scrum-master",
                },
                {
                    "description": "Task 2 - will fail",
                    "expected_output": "Task 2 complete",
                    "agent": "product-manager",
                },
                {
                    "description": "Task 3",
                    "expected_output": "Task 3 complete",
                    "agent": "architect",
                },
            ],
        }

        # Simulate task 2 failure
        def mock_execute_task_with_agent_handling(workflow_id, task_spec, task_index):
            if task_index == 1:  # Task 2 fails
                return {
                    "task_index": task_index,
                    "agent": task_spec.get("agent"),
                    "status": "failed",
                    "error": "Simulated failure",
                    "timestamp": "2025-01-01T10:00:00",
                }
            else:
                return {
                    "task_index": task_index,
                    "agent": task_spec.get("agent"),
                    "status": "success",
                    "message": f"Task {task_index} completed",
                    "timestamp": "2025-01-01T10:00:00",
                }

        # Patch the task execution method
        with patch.object(
            self.workflow_engine,
            "_execute_task_with_agent_handling",
            side_effect=mock_execute_task_with_agent_handling,
        ):
            # Act - Execute workflow (should fail at task 2)
            result = self.workflow_engine.execute_workflow(
                workflow_template, "interruption_test"
            )

            # Assert workflow failed
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_at"], 1)

            # Verify workflow was marked as interrupted
            workflow_id = result["workflow_id"]
            interrupted_state = self.state_manager.recover_state(workflow_id)
            self.assertEqual(interrupted_state["status"], "interrupted")

            # Test recovery from checkpoint
            recovery_result = self.workflow_engine.recover_workflow_from_checkpoint(
                workflow_id
            )

            self.assertIsNotNone(recovery_result)
            self.assertEqual(recovery_result["status"], "recovered")

            # Verify recovered state
            recovered_state = self.state_manager.recover_state(workflow_id)
            self.assertEqual(recovered_state["status"], "running")
            self.assertIn("recovery_checkpoint", recovered_state)

    def test_concurrent_workflow_execution(self):
        """Test concurrent execution of multiple workflows."""
        workflow_template = {
            "name": "concurrent-test-workflow",
            "tasks": [
                {
                    "description": "Simple task",
                    "expected_output": "Task complete",
                    "agent": "scrum-master",
                }
            ],
        }

        results = []
        errors = []

        def execute_workflow_instance(instance_id: int):
            """Execute a workflow instance."""
            try:
                result = self.workflow_engine.execute_workflow(
                    workflow_template, f"concurrent_workflow_{instance_id}"
                )
                results.append((instance_id, result))
            except Exception as e:
                errors.append((instance_id, str(e)))

        # Execute multiple workflows concurrently
        threads = []
        num_workflows = 3

        for i in range(num_workflows):
            thread = threading.Thread(target=execute_workflow_instance, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all workflows to complete
        for thread in threads:
            thread.join()

        # Assert all workflows completed successfully
        self.assertEqual(len(results), num_workflows)
        self.assertEqual(len(errors), 0)

        for instance_id, result in results:
            self.assertEqual(result["status"], "success")
            workflow_id = result["workflow_id"]

            # Verify each workflow has its own state
            state = self.state_manager.recover_state(workflow_id)
            self.assertIsNotNone(state)
            self.assertEqual(state["status"], "completed")

        # Verify no state corruption occurred
        active_workflows = self.state_manager.list_active_workflows()
        self.assertEqual(len(active_workflows), 0)  # All should be completed

    @patch("src.bmad_crewai.crewai_engine.Crew")
    def test_workflow_pause_and_resume(self, mock_crew_class):
        """Test workflow pause and resume functionality."""
        # Arrange
        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew

        workflow_template = {
            "name": "pause-resume-test-workflow",
            "tasks": [
                {
                    "description": "Long running task",
                    "expected_output": "Task complete",
                    "agent": "architect",
                }
            ],
        }

        # Start workflow
        result = self.workflow_engine.execute_workflow(
            workflow_template, "pause_resume_test"
        )

        # Should complete immediately in this test setup
        self.assertEqual(result["status"], "success")

        # Test pause on a running workflow by creating one manually
        workflow_id = "manual_pause_test"
        initial_state = {
            "status": "running",
            "current_step": "task_1",
            "steps_completed": [],
            "total_steps": 1,
        }

        self.state_manager.persist_state(workflow_id, initial_state)

        # Pause workflow
        pause_result = self.workflow_engine.pause_workflow(workflow_id)
        self.assertTrue(pause_result)

        # Verify paused state
        paused_state = self.state_manager.recover_state(workflow_id)
        self.assertEqual(paused_state["status"], "paused")
        self.assertIn("paused_at", paused_state)

        # Resume workflow
        resume_result = self.workflow_engine.resume_workflow(workflow_id)
        self.assertTrue(resume_result)

        # Verify resumed state
        resumed_state = self.state_manager.recover_state(workflow_id)
        self.assertEqual(resumed_state["status"], "running")
        self.assertIn("resumed_at", resumed_state)

        # Verify timeline entry was added
        timeline = resumed_state.get("execution_timeline", [])
        resume_entries = [entry for entry in timeline if entry.get("type") == "resume"]
        self.assertEqual(len(resume_entries), 1)

    @patch("src.bmad_crewai.crewai_engine.Crew")
    def test_workflow_progress_monitoring(self, mock_crew_class):
        """Test comprehensive workflow progress monitoring."""
        # Arrange
        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew

        workflow_template = {
            "name": "progress-test-workflow",
            "tasks": [
                {
                    "description": "Task 1",
                    "expected_output": "Task 1 output",
                    "agent": "scrum-master",
                },
                {
                    "description": "Task 2",
                    "expected_output": "Task 2 output",
                    "agent": "product-manager",
                },
                {
                    "description": "Task 3",
                    "expected_output": "Task 3 output",
                    "agent": "architect",
                },
                {
                    "description": "Task 4",
                    "expected_output": "Task 4 output",
                    "agent": "dev-agent",
                },
            ],
        }

        # Act
        result = self.workflow_engine.execute_workflow(
            workflow_template, "progress_test_workflow"
        )

        # Assert successful completion
        self.assertEqual(result["status"], "success")

        # Get comprehensive workflow status
        workflow_id = result["workflow_id"]
        status = self.workflow_engine.get_workflow_status(workflow_id)

        self.assertIsNotNone(status)
        self.assertEqual(status["workflow_id"], workflow_id)

        # Verify state information
        state = status["state"]
        self.assertEqual(state["status"], "completed")
        self.assertEqual(len(state["steps_completed"]), 4)
        self.assertEqual(state["total_steps"], 4)

        # Verify progress information
        progress = status["progress"]
        self.assertEqual(progress["completed"], 4)
        self.assertEqual(progress["total"], 4)
        self.assertEqual(progress["percentage"], 100.0)

        # Verify active workflow tracking is cleaned up
        active_info = status["active_info"]
        self.assertEqual(
            active_info["status"], "running"
        )  # May still be running during check

    def test_workflow_state_integrity_validation(self):
        """Test workflow state integrity validation across operations."""
        workflow_id = "integrity_test_workflow"

        # Create initial valid state
        initial_state = {
            "status": "running",
            "current_step": "initialization",
            "steps_completed": [],
            "total_steps": 3,
            "agent_handoffs": [],
            "execution_timeline": [],
        }

        self.state_manager.persist_state(workflow_id, initial_state)

        # Validate initial integrity
        integrity = self.state_manager.validate_state_integrity(workflow_id)
        self.assertTrue(integrity["is_valid"])

        # Simulate some operations
        self.state_manager.track_agent_handoff(
            workflow_id, "scrum-master", "product-manager"
        )
        self.state_manager.track_agent_handoff(
            workflow_id, "product-manager", "architect"
        )

        # Validate integrity after operations
        integrity = self.state_manager.validate_state_integrity(workflow_id)
        self.assertTrue(integrity["is_valid"])

        # Simulate corruption by manually modifying state file
        import json

        state_file = Path(self.temp_dir) / f"{workflow_id}.json"
        with open(state_file, "r") as f:
            current_state = json.load(f)

        # Remove required field
        del current_state["_metadata"]

        with open(state_file, "w") as f:
            json.dump(current_state, f)

        # Validate should detect corruption
        integrity = self.state_manager.validate_state_integrity(workflow_id)
        self.assertFalse(integrity["is_valid"])
        self.assertIn("Invalid state structure", integrity["issues"][0])

    def test_workflow_cleanup_after_completion(self):
        """Test proper cleanup of workflow state after completion."""
        workflow_id = "cleanup_test_workflow"

        # Create and complete a workflow
        workflow_template = {
            "name": "cleanup-test-workflow",
            "tasks": [
                {
                    "description": "Single task",
                    "expected_output": "Task complete",
                    "agent": "scrum-master",
                }
            ],
        }

        with patch("src.bmad_crewai.crewai_engine.Crew") as mock_crew_class:
            mock_crew = Mock()
            mock_crew_class.return_value = mock_crew

            result = self.workflow_engine.execute_workflow(
                workflow_template, workflow_id
            )

            self.assertEqual(result["status"], "success")

            # Verify state file exists
            state_file = Path(self.temp_dir) / f"{workflow_id}.json"
            self.assertTrue(state_file.exists())

            # Manually cleanup (in real scenario this might be done by a cleanup job)
            cleanup_result = self.state_manager.cleanup_workflow_state(workflow_id)
            self.assertTrue(cleanup_result)

            # Verify state file is removed
            self.assertFalse(state_file.exists())

            # Verify recovery returns None
            recovered = self.state_manager.recover_state(workflow_id)
            self.assertIsNone(recovered)


if __name__ == "__main__":
    unittest.main()
