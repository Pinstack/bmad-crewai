"""
Workflow Manager for BMAD CrewAI Integration

This module provides workflow state tracking and execution management
for BMAD processes coordinated through CrewAI.
"""

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from crewai import Process, Task

from .exceptions import BmadCrewAIError


class WorkflowStatus(Enum):
    """Enumeration of possible workflow statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    """Enumeration of possible task statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowExecutionResult:
    """
    Container for workflow execution results and metadata.

    This class encapsulates the results of a workflow execution including
    success/failure status, timing information, and detailed task results.
    """

    def __init__(self, workflow_id: str, workflow_name: str):
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.status = WorkflowStatus.PENDING
        self.task_results: Dict[str, Dict[str, Any]] = {}
        self.error_message: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    @property
    def duration(self) -> Optional[float]:
        """Get workflow execution duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "status": self.status.value,
            "task_results": self.task_results,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class WorkflowStateTracker:
    """
    State management for workflow execution and progress tracking.

    This class tracks the state of workflows and their constituent tasks,
    providing progress monitoring and status reporting capabilities.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the workflow state tracker.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.workflows: Dict[str, WorkflowExecutionResult] = {}
        self.active_workflows: Dict[str, WorkflowExecutionResult] = {}

    def start_workflow(
        self, workflow_id: str, workflow_name: str, tasks: List[Task]
    ) -> WorkflowExecutionResult:
        """
        Start tracking a new workflow execution.

        Args:
            workflow_id: Unique identifier for the workflow
            workflow_name: Human-readable name for the workflow
            tasks: List of tasks in the workflow

        Returns:
            WorkflowExecutionResult instance for tracking
        """
        if workflow_id in self.workflows:
            self.logger.warning(f"Workflow {workflow_id} already exists, overwriting")

        result = WorkflowExecutionResult(workflow_id, workflow_name)
        result.start_time = datetime.now()
        result.status = WorkflowStatus.RUNNING

        # Initialize task tracking
        for i, task in enumerate(tasks):
            task_id = f"{workflow_id}_task_{i}"
            result.task_results[task_id] = {
                "task_description": getattr(task, "description", f"Task {i}"),
                "status": TaskStatus.PENDING.value,
                "start_time": None,
                "end_time": None,
                "result": None,
                "error": None,
            }

        self.workflows[workflow_id] = result
        self.active_workflows[workflow_id] = result

        self.logger.info(f"Started tracking workflow: {workflow_name} ({workflow_id})")
        return result

    def update_task_status(
        self,
        workflow_id: str,
        task_index: int,
        status: TaskStatus,
        result: Any = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update the status of a specific task in a workflow.

        Args:
            workflow_id: Workflow identifier
            task_index: Index of the task in the workflow
            status: New task status
            result: Task execution result (if any)
            error: Error message (if status is FAILED)

        Returns:
            bool: True if update successful, False otherwise
        """
        if workflow_id not in self.workflows:
            self.logger.error(f"Workflow {workflow_id} not found")
            return False

        workflow = self.workflows[workflow_id]
        task_id = f"{workflow_id}_task_{task_index}"

        if task_id not in workflow.task_results:
            self.logger.error(f"Task {task_id} not found in workflow {workflow_id}")
            return False

        task_result = workflow.task_results[task_id]

        # Update timestamps
        if status == TaskStatus.RUNNING and not task_result["start_time"]:
            task_result["start_time"] = datetime.now().isoformat()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]:
            task_result["end_time"] = datetime.now().isoformat()

        # Update status and result
        task_result["status"] = status.value
        if result is not None:
            task_result["result"] = result
        if error:
            task_result["error"] = error

        self.logger.debug(f"Updated task {task_id} status to {status.value}")
        return True

    def complete_workflow(
        self,
        workflow_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Mark a workflow as completed.

        Args:
            workflow_id: Workflow identifier
            success: Whether the workflow completed successfully
            error_message: Error message if workflow failed

        Returns:
            bool: True if completion successful, False otherwise
        """
        if workflow_id not in self.workflows:
            self.logger.error(f"Workflow {workflow_id} not found")
            return False

        workflow = self.workflows[workflow_id]
        workflow.end_time = datetime.now()

        if success:
            workflow.status = WorkflowStatus.COMPLETED
            self.logger.info(f"Workflow {workflow_id} completed successfully")
        else:
            workflow.status = WorkflowStatus.FAILED
            workflow.error_message = error_message
            self.logger.error(f"Workflow {workflow_id} failed: {error_message}")

        # Remove from active workflows
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]

        return True

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dictionary with workflow status information or None if not found
        """
        if workflow_id not in self.workflows:
            return None

        workflow = self.workflows[workflow_id]
        return workflow.to_dict()

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get list of all currently active workflows."""
        return [workflow.to_dict() for workflow in self.active_workflows.values()]

    def get_workflow_progress(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed progress information for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dictionary with progress details or None if not found
        """
        if workflow_id not in self.workflows:
            return None

        workflow = self.workflows[workflow_id]

        total_tasks = len(workflow.task_results)
        completed_tasks = sum(
            1
            for task in workflow.task_results.values()
            if task["status"] == TaskStatus.COMPLETED.value
        )
        failed_tasks = sum(
            1
            for task in workflow.task_results.values()
            if task["status"] == TaskStatus.FAILED.value
        )
        running_tasks = sum(
            1
            for task in workflow.task_results.values()
            if task["status"] == TaskStatus.RUNNING.value
        )

        progress_percentage = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

        return {
            "workflow_id": workflow_id,
            "workflow_name": workflow.workflow_name,
            "status": workflow.status.value,
            "progress_percentage": progress_percentage,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "running_tasks": running_tasks,
            "duration": workflow.duration,
            "error_message": workflow.error_message,
        }

    def cancel_workflow(
        self, workflow_id: str, reason: str = "Cancelled by user"
    ) -> bool:
        """
        Cancel a running workflow.

        Args:
            workflow_id: Workflow identifier
            reason: Reason for cancellation

        Returns:
            bool: True if cancellation successful, False otherwise
        """
        if workflow_id not in self.active_workflows:
            self.logger.warning(f"Workflow {workflow_id} is not currently active")
            return False

        workflow = self.workflows[workflow_id]
        workflow.status = WorkflowStatus.CANCELLED
        workflow.error_message = reason
        workflow.end_time = datetime.now()

        # Mark all pending/running tasks as cancelled
        for task_result in workflow.task_results.values():
            if task_result["status"] in [
                TaskStatus.PENDING.value,
                TaskStatus.RUNNING.value,
            ]:
                task_result["status"] = TaskStatus.SKIPPED.value
                task_result["error"] = reason
                task_result["end_time"] = datetime.now().isoformat()

        # Remove from active workflows
        del self.active_workflows[workflow_id]

        self.logger.info(f"Workflow {workflow_id} cancelled: {reason}")
        return True

    def cleanup_completed_workflows(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed workflows from memory.

        Args:
            max_age_hours: Maximum age of workflows to keep (in hours)

        Returns:
            Number of workflows cleaned up
        """
        current_time = datetime.now()
        to_remove = []

        for workflow_id, workflow in self.workflows.items():
            if workflow.status in [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
            ]:
                if workflow.end_time:
                    age_hours = (
                        current_time - workflow.end_time
                    ).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        to_remove.append(workflow_id)

        for workflow_id in to_remove:
            del self.workflows[workflow_id]
            self.logger.debug(f"Cleaned up old workflow: {workflow_id}")

        self.logger.info(f"Cleaned up {len(to_remove)} old workflows")
        return len(to_remove)


class BmadWorkflowManager:
    """
    Manager class for coordinating BMAD workflows with CrewAI orchestration.

    This class provides high-level workflow management capabilities,
    integrating with the CrewAI orchestration engine for execution.
    """

    def __init__(self, crewai_engine, logger: Optional[logging.Logger] = None):
        """
        Initialize the BMAD workflow manager.

        Args:
            crewai_engine: CrewAI orchestration engine instance
            logger: Optional logger instance
        """
        self.crewai_engine = crewai_engine
        self.logger = logger or logging.getLogger(__name__)
        self.state_tracker = WorkflowStateTracker(self.logger)

    def execute_bmad_workflow(
        self, workflow_name: str, tasks: List[Task], workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a BMAD workflow using CrewAI orchestration.

        Args:
            workflow_name: Name of the workflow
            tasks: List of CrewAI tasks to execute
            workflow_id: Optional custom workflow ID

        Returns:
            Dictionary with execution results
        """
        if not workflow_id:
            workflow_id = f"{workflow_name}_{int(time.time())}"

        try:
            # Start tracking the workflow
            workflow_result = self.state_tracker.start_workflow(
                workflow_id, workflow_name, tasks
            )

            self.logger.info(f"Starting BMAD workflow: {workflow_name}")

            # Execute the workflow using CrewAI
            crew_result = self.crewai_engine.execute_workflow(tasks)

            # Update workflow completion status
            success = crew_result.get("status") == "success"
            error_message = crew_result.get("error") if not success else None

            self.state_tracker.complete_workflow(workflow_id, success, error_message)

            # Return comprehensive results
            result = {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "success": success,
                "crewai_result": crew_result,
                "workflow_details": workflow_result.to_dict(),
                "progress": self.state_tracker.get_workflow_progress(workflow_id),
            }

            return result

        except Exception as e:
            error_msg = f"Failed to execute BMAD workflow {workflow_name}: {e}"
            self.logger.error(error_msg)

            # Mark workflow as failed
            if workflow_id in self.state_tracker.workflows:
                self.state_tracker.complete_workflow(workflow_id, False, error_msg)

            return {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "success": False,
                "error": error_msg,
            }

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow."""
        return self.state_tracker.get_workflow_status(workflow_id)

    def get_workflow_progress(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get progress details for a specific workflow."""
        return self.state_tracker.get_workflow_progress(workflow_id)

    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """Get list of all active workflows."""
        return self.state_tracker.get_active_workflows()

    def cancel_workflow(
        self, workflow_id: str, reason: str = "Cancelled by user"
    ) -> bool:
        """Cancel a running workflow."""
        return self.state_tracker.cancel_workflow(workflow_id, reason)

    def cleanup_old_workflows(self, max_age_hours: int = 24) -> int:
        """Clean up old completed workflows."""
        return self.state_tracker.cleanup_completed_workflows(max_age_hours)
