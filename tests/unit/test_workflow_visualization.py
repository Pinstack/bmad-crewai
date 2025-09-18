"""
Unit tests for workflow visualization functionality.
"""

import logging
import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from src.bmad_crewai.workflow_visualizer import WorkflowVisualizer


class TestWorkflowVisualization(unittest.TestCase):
    """Test cases for workflow visualization."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger(__name__)
        self.visualizer = WorkflowVisualizer(logger=self.logger)

    def test_generate_mermaid_diagram_basic(self):
        """Test basic Mermaid diagram generation."""
        workflow_id = "test_workflow"
        workflow_state = {
            "workflow_template": {
                "tasks": [
                    {"description": "Task 1", "agent": "dev-agent"},
                    {"description": "Task 2", "agent": "qa-agent"},
                    {"description": "Task 3", "agent": "architect"},
                ]
            },
            "steps_completed": [0, 1],  # First two tasks completed
            "current_step_index": 2,
            "progress": {"completed": 2, "total": 3, "percentage": 66.7},
            "status": "running",
        }

        diagram = self.visualizer._generate_mermaid_diagram(workflow_id, workflow_state)

        # Check that diagram contains expected elements
        self.assertIn("flowchart TD", diagram)
        self.assertIn("Workflow Start: test_workflow", diagram)
        self.assertIn("✅ Task 1", diagram)
        self.assertIn("✅ Task 2", diagram)
        self.assertIn("⏳ Task 3", diagram)
        self.assertIn("Workflow End", diagram)
        self.assertIn("Progress: 2/3 (66.7%)", diagram)

    def test_generate_mermaid_diagram_with_conditional_branching(self):
        """Test Mermaid diagram generation with conditional branching."""
        workflow_id = "conditional_workflow"
        workflow_state = {
            "workflow_template": {
                "tasks": [
                    {
                        "description": "Check condition",
                        "agent": "dev-agent",
                        "branching": {"type": "on_success", "success_target": 2},
                    },
                    {"description": "Task 2", "agent": "qa-agent"},
                    {"description": "Success Task", "agent": "architect"},
                ]
            },
            "steps_completed": [0],
            "progress": {"completed": 1, "total": 3, "percentage": 33.3},
            "status": "running",
        }

        diagram = self.visualizer._generate_mermaid_diagram(workflow_id, workflow_state)

        # Check for conditional branching in diagram
        self.assertIn("T0 -->|Success| T2", diagram)

    def test_generate_ascii_diagram(self):
        """Test ASCII diagram generation."""
        workflow_id = "ascii_workflow"
        workflow_state = {
            "workflow_template": {
                "tasks": [
                    {"description": "First Task", "agent": "dev-agent"},
                    {"description": "Second Task", "agent": "qa-agent"},
                ]
            },
            "steps_completed": [0],
            "progress": {"completed": 1, "total": 2, "percentage": 50.0},
            "status": "running",
        }

        diagram = self.visualizer._generate_ascii_diagram(workflow_id, workflow_state)

        self.assertIn("Workflow: ascii_workflow", diagram)
        self.assertIn("✅ [dev-agent] First Task", diagram)
        self.assertIn("⏸️ [qa-agent] Second Task", diagram)
        self.assertIn("Progress: 1/2 (50.0%)", diagram)
        self.assertIn("Status: running", diagram)

    def test_generate_json_visualization(self):
        """Test JSON visualization generation."""
        import json

        workflow_id = "json_workflow"
        workflow_state = {
            "workflow_template": {
                "tasks": [{"description": "JSON Task", "agent": "dev-agent"}]
            },
            "steps_completed": [0],
            "progress": {"completed": 1, "total": 1, "percentage": 100.0},
            "status": "completed",
        }

        json_str = self.visualizer._generate_json_visualization(
            workflow_id, workflow_state
        )
        data = json.loads(json_str)

        self.assertEqual(data["workflow_id"], workflow_id)
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["progress"]["completed"], 1)
        self.assertEqual(len(data["tasks"]), 1)
        self.assertEqual(data["tasks"][0]["description"], "JSON Task")

    def test_collect_workflow_metrics_basic(self):
        """Test basic workflow metrics collection."""
        workflow_id = "metrics_workflow"
        workflow_state = {
            "_metadata": {"created": datetime.now().isoformat()},
            "end_time": datetime.now().isoformat(),
            "workflow_template": {"tasks": [{"description": "Task 1"}]},
            "steps_completed": [0],
            "task_results": [{"status": "success"}],
        }

        metrics = self.visualizer.collect_workflow_metrics(workflow_id, workflow_state)

        self.assertEqual(metrics["workflow_id"], workflow_id)
        self.assertIn("execution_time", metrics)
        self.assertIn("task_metrics", metrics)
        self.assertIn("agent_metrics", metrics)
        self.assertIn("error_metrics", metrics)
        self.assertIn("performance_metrics", metrics)

    def test_collect_task_metrics(self):
        """Test task metrics collection."""
        workflow_state = {
            "workflow_template": {"tasks": [{}] * 5},  # 5 tasks
            "steps_completed": [0, 1, 2],  # 3 completed
            "task_results": [
                {"status": "success"},
                {"status": "success"},
                {"status": "success"},
                {"status": "failed"},
                {"status": "pending"},
            ],
        }

        task_metrics = self.visualizer._collect_task_metrics(workflow_state)

        self.assertEqual(task_metrics["total_tasks"], 5)
        self.assertEqual(task_metrics["completed_tasks"], 3)
        self.assertEqual(task_metrics["pending_tasks"], 2)
        self.assertEqual(task_metrics["completion_rate"], 0.6)
        self.assertEqual(task_metrics["failed_tasks"], 1)

    def test_collect_agent_metrics(self):
        """Test agent metrics collection."""
        workflow_state = {
            "task_results": [
                {"agent": "dev-agent", "status": "success"},
                {"agent": "dev-agent", "status": "success"},
                {"agent": "qa-agent", "status": "failed"},
                {"agent": "qa-agent", "status": "success"},
            ]
        }

        agent_metrics = self.visualizer._collect_agent_metrics(workflow_state)

        self.assertIn("dev-agent", agent_metrics)
        self.assertIn("qa-agent", agent_metrics)
        self.assertEqual(agent_metrics["dev-agent"]["tasks"], 2)
        self.assertEqual(agent_metrics["dev-agent"]["successes"], 2)
        self.assertEqual(agent_metrics["dev-agent"]["success_rate"], 1.0)
        self.assertEqual(agent_metrics["qa-agent"]["success_rate"], 0.5)

    def test_collect_error_metrics(self):
        """Test error metrics collection."""
        workflow_state = {
            "task_results": [
                {"status": "success"},
                {"status": "failed"},
                {"status": "failed"},
                {"status": "success"},
                {"status": "success"},
            ],
            "error_recovery_attempts": [
                {"success": True},
                {"success": False},
                {"success": True},
            ],
        }

        error_metrics = self.visualizer._collect_error_metrics(workflow_state)

        self.assertEqual(error_metrics["total_errors"], 2)
        self.assertEqual(
            error_metrics["recovered_errors"], 0
        )  # Not tracked in task_results
        self.assertEqual(error_metrics["recovery_attempts"], 3)
        self.assertEqual(error_metrics["successful_recoveries"], 2)
        self.assertEqual(error_metrics["recovery_success_rate"], 2 / 3)

    def test_calculate_performance_metrics(self):
        """Test performance metrics calculation."""
        workflow_state = {
            "_metadata": {"created": datetime(2023, 1, 1, 10, 0, 0).isoformat()},
            "end_time": datetime(
                2023, 1, 1, 10, 5, 0
            ).isoformat(),  # 5 minutes = 300 seconds
            "workflow_template": {"tasks": [{}] * 10},
            "steps_completed": [0, 1, 2, 3, 4],  # 5 completed
            "task_results": [{"status": "success"}] * 5,
        }

        performance_metrics = self.visualizer._calculate_performance_metrics(
            workflow_state
        )

        self.assertEqual(
            performance_metrics["throughput"], 5 / 300
        )  # 5 tasks / 300 seconds
        self.assertEqual(
            performance_metrics["average_task_time"], 300 / 5
        )  # 300 seconds / 5 tasks
        self.assertIsInstance(performance_metrics["efficiency_score"], float)

    def test_generate_monitoring_alerts_high_error_rate(self):
        """Test monitoring alerts for high error recovery rate."""
        workflow_id = "alert_workflow"

        # Mock metrics with high error rate
        self.visualizer.metrics_store[workflow_id] = {
            "error_metrics": {"recovery_success_rate": 0.5}  # Below 0.8 threshold
        }

        alerts = self.visualizer._generate_monitoring_alerts(workflow_id)

        self.assertTrue(len(alerts) > 0)
        self.assertEqual(alerts[0]["type"], "warning")
        self.assertIn("error recovery", alerts[0]["message"].lower())

    def test_generate_monitoring_alerts_low_completion_rate(self):
        """Test monitoring alerts for low task completion rate."""
        workflow_id = "completion_workflow"

        self.visualizer.metrics_store[workflow_id] = {
            "task_metrics": {"completion_rate": 0.3}  # Below 0.5 threshold
        }

        alerts = self.visualizer._generate_monitoring_alerts(workflow_id)

        self.assertTrue(len(alerts) > 0)
        self.assertEqual(alerts[0]["type"], "error")
        self.assertIn("completion rate", alerts[0]["message"].lower())

    def test_generate_monitoring_recommendations(self):
        """Test monitoring recommendations generation."""
        workflow_id = "recommendation_workflow"

        self.visualizer.metrics_store[workflow_id] = {
            "performance_metrics": {
                "efficiency_score": 0.5,  # Below 0.7 threshold
                "throughput": 0.05,  # Below 0.1 threshold
            },
            "agent_metrics": {
                "dev-agent": {"success_rate": 0.6}  # Below 0.8 threshold
            },
        }

        recommendations = self.visualizer._generate_monitoring_recommendations(
            workflow_id
        )

        self.assertTrue(
            len(recommendations) >= 2
        )  # Should have multiple recommendations
        self.assertTrue(any("efficiency" in rec.lower() for rec in recommendations))
        self.assertTrue(any("throughput" in rec.lower() for rec in recommendations))

    def test_generate_monitoring_dashboard(self):
        """Test comprehensive monitoring dashboard generation."""
        workflow_id = "dashboard_workflow"

        # Mock some metrics
        self.visualizer.metrics_store[workflow_id] = {
            "execution_time": 300.0,
            "task_metrics": {"completion_rate": 0.8},
            "error_metrics": {"recovery_success_rate": 0.9},
        }

        dashboard = self.visualizer.generate_monitoring_dashboard(workflow_id)

        self.assertEqual(dashboard["workflow_id"], workflow_id)
        self.assertIn("timestamp", dashboard)
        self.assertIn("current_status", dashboard)
        self.assertIn("metrics", dashboard)
        self.assertIn("alerts", dashboard)
        self.assertIn("recommendations", dashboard)

    def test_export_visualization_data_multiple_formats(self):
        """Test exporting visualization data in multiple formats."""
        workflow_id = "export_workflow"

        exports = self.visualizer.export_visualization_data(
            workflow_id, ["mermaid", "ascii", "json"]
        )

        self.assertIn("mermaid", exports)
        self.assertIn("ascii", exports)
        self.assertIn("json", exports)
        self.assertEqual(len(exports), 3)

    def test_generate_workflow_diagram_error_handling(self):
        """Test error handling in diagram generation."""
        workflow_id = "error_workflow"
        workflow_state = None  # Invalid state

        diagram = self.visualizer.generate_workflow_diagram(workflow_id, workflow_state)

        self.assertIn("Error generating diagram", diagram)

    def test_collect_workflow_metrics_error_handling(self):
        """Test error handling in metrics collection."""
        workflow_id = "error_metrics"
        workflow_state = None  # Invalid state

        metrics = self.visualizer.collect_workflow_metrics(workflow_id, workflow_state)

        self.assertEqual(metrics["workflow_id"], workflow_id)
        self.assertIn("error", metrics)

    def test_resolve_branch_target_edge_cases(self):
        """Test branching target resolution edge cases."""
        # Test invalid index
        result = self.visualizer._resolve_branch_target(
            5, 0, 3
        )  # Index beyond total tasks
        self.assertIsNone(result)

        # Test invalid task reference
        result = self.visualizer._resolve_branch_target("invalid", 0, 3)
        self.assertIsNone(result)

        # Test valid task reference
        result = self.visualizer._resolve_branch_target("task_2", 0, 5)
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
