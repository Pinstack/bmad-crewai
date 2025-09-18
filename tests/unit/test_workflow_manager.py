"""
Unit tests for Workflow Manager

Tests P0 scenarios for workflow state tracking, task management,
and progress monitoring.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.bmad_crewai.workflow_manager import (
    TaskStatus,
    WorkflowExecutionResult,
    WorkflowStateTracker,
    WorkflowStatus,
)


class TestWorkflowExecutionResult:
    """Test suite for WorkflowExecutionResult."""

    def test_initialization(self):
        """Test WorkflowExecutionResult initialization."""
        # Act
        result = WorkflowExecutionResult("test-workflow", "Test Workflow")

        # Assert
        assert result.workflow_id == "test-workflow"
        assert result.workflow_name == "Test Workflow"
        assert result.status == WorkflowStatus.PENDING
        assert result.task_results == {}
        assert result.start_time is None
        assert result.end_time is None

    def test_duration_without_times(self):
        """Test duration calculation when times are not set."""
        # Arrange
        result = WorkflowExecutionResult("test", "Test")

        # Act
        duration = result.duration

        # Assert
        assert duration is None

    def test_duration_with_times(self):
        """Test duration calculation with start and end times."""
        # Arrange
        result = WorkflowExecutionResult("test", "Test")
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)

        result.start_time = start_time
        result.end_time = end_time

        # Act
        duration = result.duration

        # Assert
        assert duration == 30.0

    def test_to_dict(self):
        """Test conversion to dictionary representation."""
        # Arrange
        result = WorkflowExecutionResult("test-workflow", "Test Workflow")
        result.status = WorkflowStatus.COMPLETED
        result.error_message = "Test error"

        # Act
        result_dict = result.to_dict()

        # Assert
        assert result_dict["workflow_id"] == "test-workflow"
        assert result_dict["workflow_name"] == "Test Workflow"
        assert result_dict["status"] == "completed"
        assert result_dict["error_message"] == "Test error"


class TestWorkflowStateTracker:
    """Test suite for WorkflowStateTracker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = WorkflowStateTracker()

    def test_initialization(self):
        """Test WorkflowStateTracker initialization."""
        # Assert
        assert self.tracker.workflows == {}
        assert self.tracker.active_workflows == {}

    @patch("src.bmad_crewai.workflow_manager.datetime")
    def test_start_workflow(self, mock_datetime):
        """Test starting a new workflow."""
        # Arrange
        mock_now = datetime(2025, 1, 17, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        mock_task1 = Mock()
        mock_task1.description = "Task 1"
        mock_task2 = Mock()
        mock_task2.description = "Task 2"

        tasks = [mock_task1, mock_task2]

        # Act
        result = self.tracker.start_workflow("test-workflow", "Test Workflow", tasks)

        # Assert
        assert result.workflow_id == "test-workflow"
        assert result.workflow_name == "Test Workflow"
        assert result.status == WorkflowStatus.RUNNING
        assert result.start_time == mock_now

        # Check task results
        assert len(result.task_results) == 2
        assert "test-workflow_task_0" in result.task_results
        assert "test-workflow_task_1" in result.task_results

        # Check workflow is tracked
        assert "test-workflow" in self.tracker.workflows
        assert "test-workflow" in self.tracker.active_workflows

    def test_update_task_status_success(self):
        """Test successful task status update."""
        # Arrange
        result = WorkflowExecutionResult("test-workflow", "Test Workflow")
        result.task_results = {
            "test-workflow_task_0": {
                "status": TaskStatus.PENDING.value,
                "start_time": None,
                "end_time": None,
                "result": None,
                "error": None,
            }
        }
        self.tracker.workflows["test-workflow"] = result

        # Act
        success = self.tracker.update_task_status(
            "test-workflow", 0, TaskStatus.COMPLETED, "task result"
        )

        # Assert
        assert success is True
        task_result = result.task_results["test-workflow_task_0"]
        assert task_result["status"] == TaskStatus.COMPLETED.value
        assert task_result["result"] == "task result"
        assert task_result["end_time"] is not None

    def test_update_task_status_workflow_not_found(self):
        """Test task status update for non-existent workflow."""
        # Act
        success = self.tracker.update_task_status(
            "nonexistent", 0, TaskStatus.COMPLETED
        )

        # Assert
        assert success is False

    def test_update_task_status_task_not_found(self):
        """Test task status update for non-existent task."""
        # Arrange
        result = WorkflowExecutionResult("test-workflow", "Test Workflow")
        self.tracker.workflows["test-workflow"] = result

        # Act
        success = self.tracker.update_task_status(
            "test-workflow", 999, TaskStatus.COMPLETED
        )

        # Assert
        assert success is False

    @patch("src.bmad_crewai.workflow_manager.datetime")
    def test_complete_workflow_success(self, mock_datetime):
        """Test successful workflow completion."""
        # Arrange
        mock_now = datetime(2025, 1, 17, 10, 30, 0)
        mock_datetime.now.return_value = mock_now

        result = WorkflowExecutionResult("test-workflow", "Test Workflow")
        result.start_time = datetime(2025, 1, 17, 10, 0, 0)
        result.status = WorkflowStatus.RUNNING
        self.tracker.workflows["test-workflow"] = result
        self.tracker.active_workflows["test-workflow"] = result

        # Act
        success = self.tracker.complete_workflow("test-workflow", success=True)

        # Assert
        assert success is True
        assert result.status == WorkflowStatus.COMPLETED
        assert result.end_time == mock_now
        assert "test-workflow" not in self.tracker.active_workflows

    @patch("src.bmad_crewai.workflow_manager.datetime")
    def test_complete_workflow_failure(self, mock_datetime):
        """Test workflow completion with failure."""
        # Arrange
        mock_now = datetime(2025, 1, 17, 10, 30, 0)
        mock_datetime.now.return_value = mock_now

        result = WorkflowExecutionResult("test-workflow", "Test Workflow")
        result.status = WorkflowStatus.RUNNING
        self.tracker.workflows["test-workflow"] = result
        self.tracker.active_workflows["test-workflow"] = result

        # Act
        success = self.tracker.complete_workflow(
            "test-workflow", success=False, error_message="Test error"
        )

        # Assert
        assert success is True
        assert result.status == WorkflowStatus.FAILED
        assert result.error_message == "Test error"
        assert result.end_time == mock_now
        assert "test-workflow" not in self.tracker.active_workflows

    def test_get_workflow_status_existing(self):
        """Test getting status of existing workflow."""
        # Arrange
        result = WorkflowExecutionResult("test-workflow", "Test Workflow")
        result.status = WorkflowStatus.COMPLETED
        self.tracker.workflows["test-workflow"] = result

        # Act
        status = self.tracker.get_workflow_status("test-workflow")

        # Assert
        assert status is not None
        assert status["workflow_id"] == "test-workflow"
        assert status["status"] == "completed"

    def test_get_workflow_status_nonexistent(self):
        """Test getting status of non-existent workflow."""
        # Act
        status = self.tracker.get_workflow_status("nonexistent")

        # Assert
        assert status is None

    def test_get_active_workflows_empty(self):
        """Test getting active workflows when none exist."""
        # Act
        active = self.tracker.get_active_workflows()

        # Assert
        assert active == []

    def test_get_active_workflows_with_active(self):
        """Test getting active workflows."""
        # Arrange
        result = WorkflowExecutionResult("test-workflow", "Test Workflow")
        result.status = WorkflowStatus.RUNNING
        self.tracker.active_workflows["test-workflow"] = result

        # Act
        active = self.tracker.get_active_workflows()

        # Assert
        assert len(active) == 1
        assert active[0]["workflow_id"] == "test-workflow"

    def test_get_workflow_progress_existing(self):
        """Test getting progress of existing workflow."""
        # Arrange
        result = WorkflowExecutionResult("test-workflow", "Test Workflow")
        result.task_results = {
            "task_0": {"status": TaskStatus.COMPLETED.value},
            "task_1": {"status": TaskStatus.COMPLETED.value},
            "task_2": {"status": TaskStatus.PENDING.value},
        }
        self.tracker.workflows["test-workflow"] = result

        # Act
        progress = self.tracker.get_workflow_progress("test-workflow")

        # Assert
        assert progress is not None
        assert progress["workflow_id"] == "test-workflow"
        assert abs(progress["progress_percentage"] - 66.67) < 0.01  # 2/3 completed
        assert progress["completed_tasks"] == 2
        assert progress["total_tasks"] == 3

    def test_get_workflow_progress_nonexistent(self):
        """Test getting progress of non-existent workflow."""
        # Act
        progress = self.tracker.get_workflow_progress("nonexistent")

        # Assert
        assert progress is None

    def test_cancel_workflow_existing_active(self):
        """Test canceling an existing active workflow."""
        # Arrange
        result = WorkflowExecutionResult("test-workflow", "Test Workflow")
        result.status = WorkflowStatus.RUNNING
        result.task_results = {
            "task_0": {
                "status": TaskStatus.RUNNING.value,
                "start_time": "2025-01-17T10:00:00",
            },
            "task_1": {"status": TaskStatus.PENDING.value},
        }
        self.tracker.workflows["test-workflow"] = result
        self.tracker.active_workflows["test-workflow"] = result

        # Act
        success = self.tracker.cancel_workflow(
            "test-workflow", "User requested cancellation"
        )

        # Assert
        assert success is True
        assert result.status == WorkflowStatus.CANCELLED
        assert result.error_message == "User requested cancellation"
        assert result.end_time is not None
        assert result.task_results["task_0"]["status"] == TaskStatus.SKIPPED.value
        assert result.task_results["task_1"]["status"] == TaskStatus.SKIPPED.value
        assert "test-workflow" not in self.tracker.active_workflows

    def test_cancel_workflow_not_active(self):
        """Test canceling a workflow that is not currently active."""
        # Act
        success = self.tracker.cancel_workflow("nonexistent", "Test reason")

        # Assert
        assert success is False

    def test_cleanup_completed_workflows(self):
        """Test cleaning up old completed workflows."""
        # Arrange
        old_result = WorkflowExecutionResult("old-workflow", "Old Workflow")
        old_result.status = WorkflowStatus.COMPLETED
        old_result.end_time = datetime.now() - timedelta(
            hours=25
        )  # Older than 24 hours

        new_result = WorkflowExecutionResult("new-workflow", "New Workflow")
        new_result.status = WorkflowStatus.COMPLETED
        new_result.end_time = datetime.now() - timedelta(
            hours=1
        )  # Less than 24 hours old

        self.tracker.workflows = {
            "old-workflow": old_result,
            "new-workflow": new_result,
        }

        # Act
        cleaned_count = self.tracker.cleanup_completed_workflows(max_age_hours=24)

        # Assert
        assert cleaned_count == 1
        assert "old-workflow" not in self.tracker.workflows
        assert "new-workflow" in self.tracker.workflows
