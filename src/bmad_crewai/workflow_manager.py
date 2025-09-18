"""
Workflow Manager for BMAD CrewAI Integration

This module provides workflow state tracking and execution management
for BMAD processes coordinated through CrewAI.
"""

import asyncio
import logging
import statistics
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from typing import Any, Callable, DefaultDict, Dict, List, Optional

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

    def list_workflows(self, filter_type: str = "all") -> List[Dict[str, Any]]:
        """
        List workflows with optional filtering.

        Args:
            filter_type: Filter type ('all', 'active', 'completed', 'failed')

        Returns:
            List of workflow dictionaries
        """
        all_workflows = [workflow.to_dict() for workflow in self.workflows.values()]

        if filter_type == "all":
            return all_workflows
        elif filter_type == "active":
            return [w for w in all_workflows if w["status"] in ["running", "pending"]]
        elif filter_type == "completed":
            return [w for w in all_workflows if w["status"] == "completed"]
        elif filter_type == "failed":
            return [w for w in all_workflows if w["status"] == "failed"]
        else:
            return all_workflows

    def get_workflow_details(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Detailed workflow information or None if not found
        """
        if workflow_id not in self.workflows:
            return None

        workflow = self.workflows[workflow_id]
        progress = self.get_workflow_progress(workflow_id)

        return {
            "workflow_id": workflow_id,
            "workflow_name": workflow.workflow_name,
            "status": workflow.status.value,
            "start_time": (
                workflow.start_time.isoformat() if workflow.start_time else None
            ),
            "end_time": workflow.end_time.isoformat() if workflow.end_time else None,
            "duration": workflow.duration,
            "error_message": workflow.error_message,
            "task_results": workflow.task_results,
            "metadata": workflow.metadata,
            "progress": progress,
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


class WorkflowMetricsCollector:
    """
    Collects and analyzes workflow execution metrics for performance monitoring.

    This class captures execution timing, step performance, and identifies
    performance bottlenecks across workflow executions.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the workflow metrics collector.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.execution_metrics: Dict[str, Dict[str, Any]] = {}
        self.performance_history: DefaultDict[str, List[float]] = defaultdict(list)
        self.bottleneck_threshold = 5.0  # seconds

        # Performance optimization: Asynchronous processing
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="metrics")
        self._async_enabled = True
        self._processing_queue: List[Dict[str, Any]] = []
        self._queue_lock = threading.Lock()
        self._shutdown_event = threading.Event()

        # Initialize thread (will be started when needed)
        self._processing_thread = None

    def _start_background_processing(self) -> None:
        """Start the background processing thread if not already started."""
        if self._processing_thread is None or not self._processing_thread.is_alive():
            self._processing_thread = threading.Thread(
                target=self._background_processor, daemon=True, name="metrics-processor"
            )
            self._processing_thread.start()

    def _background_processor(self) -> None:
        """Process queued analysis requests in the background."""
        try:
            while True:
                request = None
                with self._queue_lock:
                    if self._processing_queue:
                        request = self._processing_queue.pop(0)

                if request is None:
                    if self._shutdown_event.is_set():
                        break
                    time.sleep(0.05)
                    continue

                try:
                    workflow_id = request.get("workflow_id")
                    execution_data = request.get("execution_data", {})
                    basic_metrics = request.get("basic_metrics", {})

                    detailed = self._perform_detailed_analysis(
                        workflow_id, execution_data, basic_metrics
                    )
                    self.execution_metrics[workflow_id] = detailed
                except Exception as e:
                    self.logger.warning(f"Metrics background processing failed: {e}")

        except Exception as e:
            self.logger.error(f"Background processor crashed: {e}")

    def _perform_detailed_analysis(
        self,
        workflow_id: str,
        execution_data: Dict[str, Any],
        basic_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute detailed metrics from execution data."""
        try:
            task_results = execution_data.get("task_results", {})
            task_metrics = (
                self._analyze_task_performance(task_results)
                if isinstance(task_results, dict)
                else {
                    "task_durations": [],
                    "average_task_duration": 0,
                    "task_success_rate": 0,
                }
            )

            bottlenecks = self._identify_bottlenecks(task_metrics)
            efficiency = self._calculate_efficiency_metrics(task_metrics)

            detailed = {
                **basic_metrics,
                "task_metrics": task_metrics,
                "bottlenecks": bottlenecks,
                "efficiency_metrics": efficiency,
            }

            return detailed
        except Exception as e:
            self.logger.error(f"Detailed analysis failed for {workflow_id}: {e}")
            return {**basic_metrics, "error": str(e)}

    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Aggregate metrics across all recorded workflows."""
        try:
            if not self.execution_metrics:
                return {"no_data": True}

            durations = [
                m.get("duration")
                for m in self.execution_metrics.values()
                if m.get("duration") is not None
            ]
            success_rates = [
                m.get("task_metrics", {}).get("task_success_rate", 0)
                for m in self.execution_metrics.values()
            ]

            return {
                "total_workflows": len(self.execution_metrics),
                "average_duration": statistics.mean(durations) if durations else 0,
                "average_success_rate": (
                    statistics.mean(success_rates) if success_rates else 0
                ),
            }
        except Exception as e:
            self.logger.error(f"Failed to aggregate metrics: {e}")
            return {"error": str(e)}

    def collect_execution_metrics(
        self, workflow_id: str, execution_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Collect comprehensive workflow execution metrics.

        Args:
            workflow_id: Unique workflow identifier
            execution_data: Execution data including timing and results

        Returns:
            Dictionary with collected metrics
        """
        try:
            # Quick validation and basic metrics extraction (fast path)
            start_time = execution_data.get("start_time")
            end_time = execution_data.get("end_time")
            task_results = execution_data.get("task_results", {})

            # Calculate basic duration (fast)
            duration = None
            if start_time and end_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    )
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                duration = (end_time - start_time).total_seconds()

            # Create basic metrics structure
            basic_metrics = {
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "total_tasks": len(task_results),
                "completed_tasks": sum(
                    1 for t in task_results.values() if t.get("status") == "completed"
                ),
                "failed_tasks": sum(
                    1 for t in task_results.values() if t.get("status") == "failed"
                ),
            }

            # Compute detailed metrics synchronously for immediate availability
            detailed_metrics = self._perform_detailed_analysis(
                workflow_id, execution_data, basic_metrics
            )

            # Store metrics
            self.execution_metrics[workflow_id] = detailed_metrics
            if duration:
                self.performance_history[workflow_id].append(duration)

            self.logger.info(
                f"Collected metrics for workflow {workflow_id}: {duration:.2f}s"
            )
            return detailed_metrics

        except Exception as e:
            self.logger.error(
                f"Failed to collect metrics for workflow {workflow_id}: {e}"
            )
            return {"error": str(e)}

    def _analyze_task_performance(self, task_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze individual task performance metrics."""
        task_durations = []
        task_success_rate = {}

        for task_id, task_data in task_results.items():
            # Calculate task duration
            start_time = task_data.get("start_time")
            end_time = task_data.get("end_time")

            if start_time and end_time:
                try:
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(
                            start_time.replace("Z", "+00:00")
                        )
                    if isinstance(end_time, str):
                        end_time = datetime.fromisoformat(
                            end_time.replace("Z", "+00:00")
                        )

                    duration = (end_time - start_time).total_seconds()
                    task_durations.append(duration)
                    task_success_rate[task_id] = task_data.get("status") == "completed"
                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse timing for task {task_id}: {e}"
                    )

        return {
            "task_durations": task_durations,
            "average_task_duration": (
                statistics.mean(task_durations) if task_durations else 0
            ),
            "max_task_duration": max(task_durations) if task_durations else 0,
            "min_task_duration": min(task_durations) if task_durations else 0,
            "task_success_rate": (
                sum(task_success_rate.values()) / len(task_success_rate)
                if task_success_rate
                else 0
            ),
        }

    def _identify_bottlenecks(
        self, task_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks in workflow execution."""
        bottlenecks = []
        task_durations = task_metrics.get("task_durations", [])
        avg_duration = task_metrics.get("average_task_duration", 0)

        # Find tasks that exceed average duration significantly
        for i, duration in enumerate(task_durations):
            if duration > avg_duration * 2:  # Tasks taking 2x the average
                bottlenecks.append(
                    {
                        "task_index": i,
                        "duration": duration,
                        "deviation_from_average": duration - avg_duration,
                        "severity": "high" if duration > avg_duration * 2 else "medium",
                    }
                )

        return bottlenecks

    def _calculate_efficiency_metrics(
        self, task_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate workflow efficiency metrics."""
        task_durations = task_metrics.get("task_durations", [])

        if not task_durations:
            return {"efficiency_score": 0, "variability_coefficient": 0}

        # Calculate coefficient of variation (lower is better)
        mean_duration = statistics.mean(task_durations)
        std_dev = statistics.stdev(task_durations) if len(task_durations) > 1 else 0
        cv = (std_dev / mean_duration) if mean_duration > 0 else 0

        # Efficiency score (higher is better): inverse of variability (less aggressive scaling)
        efficiency_score = max(0, 100 - (cv * 50))

        return {
            "efficiency_score": efficiency_score,
            "variability_coefficient": cv,
            "consistency_rating": (
                "high" if cv < 0.3 else "medium" if cv < 0.6 else "low"
            ),
        }

    def get_workflow_performance_trends(self, workflow_id: str) -> Dict[str, Any]:
        """Get performance trends for a specific workflow."""
        history = self.performance_history.get(workflow_id, [])

        if len(history) < 2:
            return {"insufficient_data": True}

        return {
            "total_executions": len(history),
            "average_duration": statistics.mean(history),
            "trend_direction": "improving" if history[-1] < history[0] else "degrading",
            "performance_variance": (
                statistics.stdev(history) if len(history) > 1 else 0
            ),
        }

    def _queue_analysis_request(self, analysis_request: Dict[str, Any]) -> None:
        """Queue a detailed analysis request for background processing."""
        with self._queue_lock:
            self._processing_queue.append(analysis_request)
        # Ensure background processing is started
        self._start_background_processing()


class WorkflowOptimizer:
    """
    Analyzes workflow performance data and generates optimization recommendations.

    This class identifies bottlenecks, suggests improvements, and prioritizes
    optimization opportunities based on performance impact and implementation effort.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the workflow optimizer.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def generate_recommendations(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze metrics data and generate optimization recommendations.

        Args:
            metrics_data: Metrics data from WorkflowMetricsCollector

        Returns:
            Dictionary with optimization recommendations
        """
        recommendations = []
        priority_score = 0

        try:
            # Analyze bottlenecks
            bottlenecks = metrics_data.get("bottlenecks", [])
            if bottlenecks:
                bottleneck_recs = self._analyze_bottlenecks(bottlenecks)
                recommendations.extend(bottleneck_recs)

            # Analyze efficiency metrics
            efficiency = metrics_data.get("efficiency_metrics", {})
            if efficiency:
                efficiency_recs = self._analyze_efficiency(efficiency)
                recommendations.extend(efficiency_recs)

            # Analyze task performance
            task_metrics = metrics_data.get("task_metrics", {})
            if task_metrics:
                task_recs = self._analyze_task_patterns(task_metrics)
                recommendations.extend(task_recs)

            # Calculate overall priority score
            priority_score = self._calculate_priority_score(recommendations)

            # Sort recommendations by priority
            recommendations.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

            result = {
                "workflow_id": metrics_data.get("workflow_id"),
                "recommendations": recommendations,
                "priority_score": priority_score,
                "optimization_potential": self._calculate_optimization_potential(
                    recommendations
                ),
                "implementation_effort": self._estimate_implementation_effort(
                    recommendations
                ),
            }

            self.logger.info(
                f"Generated {len(recommendations)} optimization recommendations"
            )
            return result

        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}")
            return {"error": str(e)}

    def _analyze_bottlenecks(
        self, bottlenecks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze identified bottlenecks and generate recommendations."""
        recommendations = []

        for bottleneck in bottlenecks:
            severity = bottleneck.get("severity", "low")
            duration = bottleneck.get("duration", 0)
            task_index = bottleneck.get("task_index", 0)

            if severity == "high":
                recommendations.append(
                    {
                        "type": "bottleneck_optimization",
                        "title": f"Optimize Task {task_index} Performance",
                        "description": f"Task {task_index} is taking {duration:.2f}s, significantly impacting workflow performance",
                        "impact": "high",
                        "effort": "medium",
                        "priority_score": 90,
                        "suggestions": [
                            "Review task implementation for optimization opportunities",
                            "Consider parallel execution if tasks are independent",
                            "Implement caching for frequently accessed data",
                            "Profile code execution to identify hotspots",
                        ],
                    }
                )
            elif severity == "medium":
                recommendations.append(
                    {
                        "type": "performance_improvement",
                        "title": f"Improve Task {task_index} Efficiency",
                        "description": f"Task {task_index} duration ({duration:.2f}s) exceeds average",
                        "impact": "medium",
                        "effort": "low",
                        "priority_score": 70,
                        "suggestions": [
                            "Review error handling and retry logic",
                            "Optimize data access patterns",
                            "Consider asynchronous processing",
                        ],
                    }
                )

        return recommendations

    def _analyze_efficiency(
        self, efficiency_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze workflow efficiency and generate recommendations."""
        recommendations = []
        efficiency_score = efficiency_metrics.get("efficiency_score", 0)
        consistency_rating = efficiency_metrics.get("consistency_rating", "low")
        variability_coeff = efficiency_metrics.get("variability_coefficient", 1.0)

        # Low efficiency recommendations
        if efficiency_score < 50:
            recommendations.append(
                {
                    "type": "efficiency_optimization",
                    "title": "Improve Workflow Consistency",
                    "description": f"Workflow efficiency score is {efficiency_score:.1f}%, indicating inconsistent performance",
                    "impact": "high",
                    "effort": "medium",
                    "priority_score": 85,
                    "suggestions": [
                        "Standardize task execution patterns",
                        "Implement consistent error handling",
                        "Review resource allocation across tasks",
                        "Consider workflow orchestration improvements",
                    ],
                }
            )

        # High variability recommendations
        if variability_coeff > 0.6:
            recommendations.append(
                {
                    "type": "variability_reduction",
                    "title": "Reduce Execution Variability",
                    "description": f"High task duration variability (coefficient: {variability_coeff:.2f})",
                    "impact": "medium",
                    "effort": "medium",
                    "priority_score": 75,
                    "suggestions": [
                        "Implement consistent timeout handling",
                        "Standardize resource allocation",
                        "Add performance monitoring and alerting",
                        "Review external dependency reliability",
                    ],
                }
            )

        return recommendations

    def _analyze_task_patterns(
        self, task_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze task execution patterns and generate recommendations."""
        recommendations = []
        success_rate = task_metrics.get("task_success_rate", 0)
        avg_duration = task_metrics.get("average_task_duration", 0)

        # Low success rate recommendations
        if success_rate < 0.8:
            recommendations.append(
                {
                    "type": "reliability_improvement",
                    "title": "Improve Task Success Rate",
                    "description": f"Task success rate is {success_rate:.1%}, below acceptable threshold",
                    "impact": "high",
                    "effort": "medium",
                    "priority_score": 95,
                    "suggestions": [
                        "Review and improve error handling",
                        "Implement retry mechanisms for transient failures",
                        "Add input validation and sanitization",
                        "Monitor and analyze failure patterns",
                    ],
                }
            )

        # Long-running tasks recommendations
        if avg_duration > 10:  # More than 10 seconds average
            recommendations.append(
                {
                    "type": "performance_optimization",
                    "title": "Optimize Long-Running Tasks",
                    "description": f"Average task duration ({avg_duration:.1f}s) indicates performance issues",
                    "impact": "medium",
                    "effort": "high",
                    "priority_score": 80,
                    "suggestions": [
                        "Break down complex tasks into smaller steps",
                        "Implement progress tracking and cancellation",
                        "Consider background processing for long operations",
                        "Optimize data processing algorithms",
                    ],
                }
            )

        return recommendations

    def _calculate_priority_score(self, recommendations: List[Dict[str, Any]]) -> float:
        """Calculate overall priority score for optimization recommendations."""
        if not recommendations:
            return 0

        total_score = sum(rec.get("priority_score", 0) for rec in recommendations)
        return total_score / len(recommendations)

    def _calculate_optimization_potential(
        self, recommendations: List[Dict[str, Any]]
    ) -> str:
        """Estimate the optimization potential based on recommendations."""
        high_impact = sum(1 for rec in recommendations if rec.get("impact") == "high")
        total_recs = len(recommendations)

        if total_recs == 0:
            return "none"
        elif high_impact / total_recs > 0.5:
            return "high"
        elif high_impact / total_recs > 0.25:
            return "medium"
        else:
            return "low"

    def _estimate_implementation_effort(
        self, recommendations: List[Dict[str, Any]]
    ) -> str:
        """Estimate overall implementation effort."""
        effort_weights = {"low": 1, "medium": 2, "high": 3}
        total_effort = sum(
            effort_weights.get(rec.get("effort", "medium"), 2)
            for rec in recommendations
        )

        if total_effort <= len(recommendations):
            return "low"
        elif total_effort <= len(recommendations) * 2:
            return "medium"
        else:
            return "high"


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
        self.metrics_collector = WorkflowMetricsCollector(self.logger)
        self.optimizer = WorkflowOptimizer(self.logger)

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

            # Collect performance metrics
            workflow_details = workflow_result.to_dict()
            metrics = self.metrics_collector.collect_execution_metrics(
                workflow_id, workflow_details
            )

            # Generate optimization recommendations
            recommendations = self.optimizer.generate_recommendations(metrics)

            # Return comprehensive results
            result = {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "success": success,
                "crewai_result": crew_result,
                "workflow_details": workflow_details,
                "progress": self.state_tracker.get_workflow_progress(workflow_id),
                "metrics": metrics,
                "recommendations": recommendations,
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

    def get_workflow_metrics(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific workflow."""
        if workflow_id in self.metrics_collector.execution_metrics:
            return self.metrics_collector.execution_metrics[workflow_id]
        return None

    def get_workflow_performance_trends(self, workflow_id: str) -> Dict[str, Any]:
        """Get performance trends for a specific workflow."""
        return self.metrics_collector.get_workflow_performance_trends(workflow_id)

    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics across all workflows."""
        return self.metrics_collector.get_aggregated_metrics()

    def get_workflow_optimization_recommendations(
        self, workflow_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get optimization recommendations for a specific workflow."""
        metrics = self.get_workflow_metrics(workflow_id)
        if metrics:
            return self.optimizer.generate_recommendations(metrics)
        return None
