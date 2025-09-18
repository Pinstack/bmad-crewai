"""
Workflow Visualizer for BMAD CrewAI Integration

This module provides comprehensive workflow visualization and monitoring capabilities
for the BMAD framework, including Mermaid diagram generation and real-time metrics.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .exceptions import BmadCrewAIError


class WorkflowVisualizer:
    """
    Comprehensive workflow visualizer with Mermaid diagram generation and monitoring.

    Provides real-time workflow visualization, execution metrics, and performance
    monitoring capabilities for BMAD workflow orchestration.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the workflow visualizer.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.visualization_cache: Dict[str, Dict[str, Any]] = {}
        self.metrics_store: Dict[str, Dict[str, Any]] = {}

        self.logger.info("WorkflowVisualizer initialized")

    def generate_workflow_diagram(
        self,
        workflow_id: str,
        workflow_state: Dict[str, Any],
        workflow_template: Optional[Dict[str, Any]] = None,
        format: str = "mermaid",
    ) -> str:
        """
        Generate a visual diagram of the workflow execution state.

        Args:
            workflow_id: Workflow identifier
            workflow_state: Current workflow state
            workflow_template: Optional workflow template for additional context
            format: Output format ("mermaid", "ascii", "json")

        Returns:
            str: Generated diagram in specified format
        """
        try:
            if format == "mermaid":
                return self._generate_mermaid_diagram(
                    workflow_id, workflow_state, workflow_template
                )
            elif format == "ascii":
                return self._generate_ascii_diagram(
                    workflow_id, workflow_state, workflow_template
                )
            elif format == "json":
                return self._generate_json_visualization(
                    workflow_id, workflow_state, workflow_template
                )
            else:
                raise BmadCrewAIError(f"Unsupported visualization format: {format}")

        except Exception as e:
            self.logger.error(f"Failed to generate workflow diagram: {e}")
            return f"Error generating diagram: {str(e)}"

    def _generate_mermaid_diagram(
        self,
        workflow_id: str,
        workflow_state: Dict[str, Any],
        workflow_template: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate Mermaid flowchart diagram."""
        diagram_lines = [
            "flowchart TD",
            f"    Start([Workflow Start: {workflow_id}])",
        ]

        # Add tasks
        tasks = workflow_state.get("workflow_template", {}).get("tasks", [])
        steps_completed = workflow_state.get("steps_completed", [])

        for i, task in enumerate(tasks):
            task_id = f"T{i}"
            task_desc = task.get("description", f"Task {i}").replace('"', "'")[:30]
            status = (
                "✅"
                if i in steps_completed
                else "⏳" if i == workflow_state.get("current_step_index", -1) else "⏸️"
            )

            # Determine task style based on status
            if i in steps_completed:
                diagram_lines.append(f'    {task_id}["{status} {task_desc}"]')
                diagram_lines.append(f"    style {task_id} fill:#d4edda")
            elif i == workflow_state.get("current_step_index", -1):
                diagram_lines.append(f'    {task_id}["{status} {task_desc}"]')
                diagram_lines.append(f"    style {task_id} fill:#fff3cd")
            else:
                diagram_lines.append(f'    {task_id}["{status} {task_desc}"]')

        # Add conditional branching if present
        self._add_conditional_branching_diagram(tasks, diagram_lines)

        # Add connections
        self._add_task_connections(tasks, diagram_lines, steps_completed)

        # Add end node
        diagram_lines.append(f"    End([Workflow End])")

        # Add execution metadata
        self._add_execution_metadata_diagram(workflow_state, diagram_lines)

        return "\n".join(diagram_lines)

    def _add_conditional_branching_diagram(
        self, tasks: List[Dict[str, Any]], diagram_lines: List[str]
    ) -> None:
        """Add conditional branching elements to the diagram."""
        for i, task in enumerate(tasks):
            branching = task.get("branching")
            if branching:
                task_id = f"T{i}"
                branching_type = branching.get("type")

                if branching_type == "on_success":
                    success_target = branching.get("success_target")
                    if success_target is not None:
                        diagram_lines.append(
                            f"    {task_id} -->|Success| T{success_target}"
                        )

                elif branching_type == "on_failure":
                    failure_target = branching.get("failure_target")
                    if failure_target is not None:
                        diagram_lines.append(
                            f"    {task_id} -->|Failure| T{failure_target}"
                        )

                elif branching_type == "conditional":
                    conditions = branching.get("conditions", [])
                    for j, condition in enumerate(conditions):
                        target = condition.get("target")
                        label = condition.get("label", f"Condition {j+1}")
                        if target is not None:
                            diagram_lines.append(
                                f"    {task_id} -->|{label}| T{target}"
                            )

    def _add_task_connections(
        self,
        tasks: List[Dict[str, Any]],
        diagram_lines: List[str],
        steps_completed: List[int],
    ) -> None:
        """Add task-to-task connections in the diagram."""
        for i in range(len(tasks) - 1):
            current_task = tasks[i]
            next_task = tasks[i + 1]

            # Skip if conditional branching is defined for current task
            if current_task.get("branching"):
                continue

            # Add connection with status indicator
            connection_label = ""
            if i in steps_completed:
                connection_label = "✅"
            elif i + 1 in steps_completed:
                connection_label = "🔄"

            if connection_label:
                diagram_lines.append(f"    T{i} -->|{connection_label}| T{i+1}")
            else:
                diagram_lines.append(f"    T{i} --> T{i+1}")

    def _add_execution_metadata_diagram(
        self, workflow_state: Dict[str, Any], diagram_lines: List[str]
    ) -> None:
        """Add execution metadata to the diagram."""
        progress = workflow_state.get("progress", {})
        completed = progress.get("completed", 0)
        total = progress.get("total", 0)
        percentage = progress.get("percentage", 0)

        diagram_lines.extend(
            [
                "",
                "    %% Execution Metadata",
                f'    Progress["Progress: {completed}/{total} ({percentage:.1f}%)"]',
                f"    Status[\"Status: {workflow_state.get('status', 'unknown')}\"]",
                "    Progress --> Status",
            ]
        )

    def _generate_ascii_diagram(
        self,
        workflow_id: str,
        workflow_state: Dict[str, Any],
        workflow_template: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate ASCII art diagram."""
        lines = [
            f"Workflow: {workflow_id}",
            "=" * 50,
        ]

        tasks = workflow_state.get("workflow_template", {}).get("tasks", [])
        steps_completed = workflow_state.get("steps_completed", [])

        for i, task in enumerate(tasks):
            status = (
                "✅"
                if i in steps_completed
                else "⏳" if i == workflow_state.get("current_step_index", -1) else "⏸️"
            )
            desc = task.get("description", f"Task {i}")[:40]
            agent = task.get("agent", "auto")
            lines.append(f"{status} [{agent}] {desc}")

            if i < len(tasks) - 1:
                lines.append("    |")
                lines.append("    v")

        # Add summary
        progress = workflow_state.get("progress", {})
        lines.extend(
            [
                "",
                f"Progress: {progress.get('completed', 0)}/{progress.get('total', 0)} ({progress.get('percentage', 0):.1f}%)",
                f"Status: {workflow_state.get('status', 'unknown')}",
            ]
        )

        return "\n".join(lines)

    def _generate_json_visualization(
        self,
        workflow_id: str,
        workflow_state: Dict[str, Any],
        workflow_template: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate JSON representation of workflow visualization."""
        import json

        visualization = {
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
            "status": workflow_state.get("status", "unknown"),
            "progress": workflow_state.get("progress", {}),
            "tasks": [],
            "connections": [],
            "metadata": {
                "total_tasks": len(
                    workflow_state.get("workflow_template", {}).get("tasks", [])
                ),
                "completed_tasks": len(workflow_state.get("steps_completed", [])),
                "current_step": workflow_state.get("current_step"),
            },
        }

        # Add task details
        tasks = workflow_state.get("workflow_template", {}).get("tasks", [])
        steps_completed = workflow_state.get("steps_completed", [])

        for i, task in enumerate(tasks):
            task_info = {
                "id": f"T{i}",
                "index": i,
                "description": task.get("description", f"Task {i}"),
                "agent": task.get("agent", "auto"),
                "status": "completed" if i in steps_completed else "pending",
                "branching": task.get("branching"),
            }
            visualization["tasks"].append(task_info)

        return json.dumps(visualization, indent=2, default=str)

    def collect_workflow_metrics(
        self,
        workflow_id: str,
        workflow_state: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Collect comprehensive workflow execution metrics.

        Args:
            workflow_id: Workflow identifier
            workflow_state: Current workflow state
            execution_result: Optional execution results

        Returns:
            Dict[str, Any]: Collected metrics
        """
        try:
            metrics = {
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": self._calculate_execution_time(workflow_state),
                "task_metrics": self._collect_task_metrics(workflow_state),
                "agent_metrics": self._collect_agent_metrics(workflow_state),
                "error_metrics": self._collect_error_metrics(workflow_state),
                "performance_metrics": self._calculate_performance_metrics(
                    workflow_state, execution_result
                ),
            }

            # Store metrics
            self.metrics_store[workflow_id] = metrics

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to collect workflow metrics: {e}")
            return {"error": str(e), "workflow_id": workflow_id}

    def _calculate_execution_time(
        self, workflow_state: Dict[str, Any]
    ) -> Optional[float]:
        """Calculate total workflow execution time."""
        try:
            start_time = workflow_state.get("_metadata", {}).get("created")
            end_time = workflow_state.get("end_time")

            if start_time and end_time:
                start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                return (end - start).total_seconds()

        except Exception as e:
            self.logger.warning(f"Failed to calculate execution time: {e}")

        return None

    def _collect_task_metrics(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Collect metrics about task execution."""
        tasks = workflow_state.get("workflow_template", {}).get("tasks", [])
        steps_completed = workflow_state.get("steps_completed", [])

        return {
            "total_tasks": len(tasks),
            "completed_tasks": len(steps_completed),
            "pending_tasks": len(tasks) - len(steps_completed),
            "completion_rate": len(steps_completed) / len(tasks) if tasks else 0,
            "failed_tasks": sum(
                1
                for result in workflow_state.get("task_results", [])
                if result.get("status") == "failed"
            ),
        }

    def _collect_agent_metrics(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Collect metrics about agent utilization."""
        agent_usage = {}
        task_results = workflow_state.get("task_results", [])

        for result in task_results:
            agent = result.get("agent")
            if agent:
                if agent not in agent_usage:
                    agent_usage[agent] = {"tasks": 0, "successes": 0, "failures": 0}
                agent_usage[agent]["tasks"] += 1
                if result.get("status") == "success":
                    agent_usage[agent]["successes"] += 1
                else:
                    agent_usage[agent]["failures"] += 1

        # Calculate success rates
        for agent, metrics in agent_usage.items():
            total = metrics["tasks"]
            if total > 0:
                metrics["success_rate"] = metrics["successes"] / total
                metrics["failure_rate"] = metrics["failures"] / total

        return agent_usage

    def _collect_error_metrics(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Collect metrics about errors and recovery."""
        task_results = workflow_state.get("task_results", [])
        error_attempts = workflow_state.get("error_recovery_attempts", [])

        return {
            "total_errors": sum(
                1 for result in task_results if result.get("status") == "failed"
            ),
            "recovered_errors": sum(
                1 for result in task_results if result.get("recovered")
            ),
            "recovery_attempts": len(error_attempts),
            "successful_recoveries": sum(
                1 for attempt in error_attempts if attempt.get("success")
            ),
            "recovery_success_rate": (
                sum(1 for attempt in error_attempts if attempt.get("success"))
                / len(error_attempts)
                if error_attempts
                else 0
            ),
        }

    def _calculate_performance_metrics(
        self,
        workflow_state: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Calculate performance metrics."""
        metrics = {
            "throughput": 0.0,  # tasks per second
            "average_task_time": 0.0,
            "bottleneck_tasks": [],
            "efficiency_score": 0.0,
        }

        try:
            execution_time = self._calculate_execution_time(workflow_state)
            task_metrics = self._collect_task_metrics(workflow_state)

            if execution_time and execution_time > 0:
                metrics["throughput"] = task_metrics["completed_tasks"] / execution_time
                metrics["average_task_time"] = (
                    execution_time / task_metrics["completed_tasks"]
                )

            # Calculate efficiency score (0-1 scale)
            completion_rate = task_metrics["completion_rate"]
            error_rate = self._collect_error_metrics(workflow_state)[
                "recovery_success_rate"
            ]
            metrics["efficiency_score"] = (completion_rate + (1 - error_rate)) / 2

        except Exception as e:
            self.logger.warning(f"Failed to calculate performance metrics: {e}")

        return metrics

    def generate_monitoring_dashboard(
        self, workflow_id: str, include_historical: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive monitoring dashboard for the workflow.

        Args:
            workflow_id: Workflow identifier
            include_historical: Whether to include historical metrics

        Returns:
            Dict[str, Any]: Monitoring dashboard data
        """
        try:
            dashboard = {
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "current_status": {},
                "metrics": {},
                "alerts": [],
                "recommendations": [],
            }

            # Get current metrics
            if workflow_id in self.metrics_store:
                dashboard["metrics"] = self.metrics_store[workflow_id]

            # Generate alerts
            dashboard["alerts"] = self._generate_monitoring_alerts(workflow_id)

            # Generate recommendations
            dashboard["recommendations"] = self._generate_monitoring_recommendations(
                workflow_id
            )

            return dashboard

        except Exception as e:
            self.logger.error(f"Failed to generate monitoring dashboard: {e}")
            return {"error": str(e), "workflow_id": workflow_id}

    def _generate_monitoring_alerts(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Generate monitoring alerts based on workflow metrics."""
        alerts = []

        try:
            metrics = self.metrics_store.get(workflow_id, {})
            error_metrics = metrics.get("error_metrics", {})

            # Check error rates
            if error_metrics.get("recovery_success_rate", 0) < 0.8:
                alerts.append(
                    {
                        "type": "warning",
                        "message": "High error recovery failure rate detected",
                        "severity": "medium",
                        "metric": "recovery_success_rate",
                        "value": error_metrics.get("recovery_success_rate", 0),
                    }
                )

            # Check task completion
            task_metrics = metrics.get("task_metrics", {})
            if task_metrics.get("completion_rate", 0) < 0.5:
                alerts.append(
                    {
                        "type": "error",
                        "message": "Low task completion rate",
                        "severity": "high",
                        "metric": "completion_rate",
                        "value": task_metrics.get("completion_rate", 0),
                    }
                )

        except Exception as e:
            self.logger.warning(f"Failed to generate monitoring alerts: {e}")

        return alerts

    def _generate_monitoring_recommendations(self, workflow_id: str) -> List[str]:
        """Generate monitoring recommendations."""
        recommendations = []

        try:
            metrics = self.metrics_store.get(workflow_id, {})
            performance_metrics = metrics.get("performance_metrics", {})

            # Performance recommendations
            if performance_metrics.get("efficiency_score", 0) < 0.7:
                recommendations.append(
                    "Consider optimizing task execution order to improve efficiency"
                )

            if performance_metrics.get("throughput", 0) < 0.1:
                recommendations.append(
                    "Workflow execution is slow; consider parallelizing independent tasks"
                )

            # Agent recommendations
            agent_metrics = metrics.get("agent_metrics", {})
            for agent, agent_data in agent_metrics.items():
                if agent_data.get("success_rate", 1.0) < 0.8:
                    recommendations.append(
                        f"Review agent {agent} performance and consider alternatives"
                    )

        except Exception as e:
            self.logger.warning(f"Failed to generate monitoring recommendations: {e}")

        return recommendations

    def export_visualization_data(
        self, workflow_id: str, formats: List[str] = None
    ) -> Dict[str, str]:
        """
        Export visualization data in multiple formats.

        Args:
            formats: List of formats to export ("mermaid", "ascii", "json", "metrics")

        Returns:
            Dict[str, str]: Exported data in requested formats
        """
        if formats is None:
            formats = ["mermaid", "ascii", "json"]

        exports = {}

        try:
            # This would need to be implemented with actual workflow state data
            # For now, return placeholder
            for fmt in formats:
                exports[fmt] = f"Visualization data for {workflow_id} in {fmt} format"

        except Exception as e:
            self.logger.error(f"Failed to export visualization data: {e}")

        return exports
