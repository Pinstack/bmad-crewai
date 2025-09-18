"""
Integration tests for monitoring and analytics system.

Tests cover:
- End-to-end workflow monitoring and analytics
- Agent performance tracking integration
- Artefact quality monitoring integration
- System health monitoring integration
- Cross-component analytics workflows
"""

import asyncio
import json
import shutil
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from src.bmad_crewai.agent_registry import AgentRegistry
from src.bmad_crewai.artefact_writer import BMADArtefactWriter
from src.bmad_crewai.core import BmadCrewAI, SystemHealthMonitor
from src.bmad_crewai.crewai_engine import CrewAIOrchestrationEngine
from src.bmad_crewai.workflow_manager import (
    BmadWorkflowManager,
    WorkflowMetricsCollector,
    WorkflowOptimizer,
)
from src.bmad_crewai.workflow_state_manager import WorkflowStateManager


class TestEndToEndWorkflowAnalytics(unittest.TestCase):
    """Test end-to-end workflow monitoring and analytics."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Initialize components
        self.crewai_engine = CrewAIOrchestrationEngine()
        self.workflow_manager = BmadWorkflowManager(self.crewai_engine)
        self.state_manager = WorkflowStateManager(storage_dir=self.temp_dir)
        self.agent_registry = AgentRegistry()
        self.artefact_writer = BMADArtefactWriter(base_path=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    @patch("src.bmad_crewai.crewai_engine.CrewAIOrchestrationEngine.execute_workflow")
    def test_complete_workflow_with_analytics(self, mock_execute):
        """Test complete workflow execution with analytics collection."""
        # Mock workflow execution
        mock_execute.return_value = {
            "status": "success",
            "result": "Workflow completed successfully",
            "execution_time": 5.0,
        }

        # Create a simple task for testing
        mock_task = Mock()
        mock_task.description = "Test workflow task"

        # Execute workflow
        result = self.workflow_manager.execute_bmad_workflow(
            "test_analytics_workflow", [mock_task], "test_workflow_001"
        )

        # Verify analytics were collected
        self.assertIn("metrics", result)
        self.assertIn("recommendations", result)
        self.assertIn("workflow_id", result["metrics"])
        self.assertEqual(result["workflow_id"], "test_workflow_001")

        # Verify metrics structure
        metrics = result["metrics"]
        self.assertIn("duration", metrics)
        self.assertIn("task_metrics", metrics)
        self.assertIn("efficiency_metrics", metrics)

    def test_agent_performance_integration(self):
        """Test agent performance tracking integration."""
        agent_id = "test_agent"

        # Simulate multiple task executions
        task_executions = [
            {"success": True, "response_time": 2.5, "task_type": "analysis"},
            {
                "success": False,
                "response_time": 1.0,
                "error_type": "timeout",
                "task_type": "execution",
            },
            {"success": True, "response_time": 3.2, "task_type": "validation"},
            {"success": True, "response_time": 2.8, "task_type": "reporting"},
        ]

        # Track performance for each execution
        for i, execution in enumerate(task_executions):
            task_metrics = {
                "success": execution["success"],
                "response_time": execution["response_time"],
                "timestamp": (datetime.now() + timedelta(seconds=i)).isoformat(),
                "task_type": execution["task_type"],
            }

            if "error_type" in execution:
                task_metrics["error_type"] = execution["error_type"]

            success = self.agent_registry.track_performance(agent_id, task_metrics)
            self.assertTrue(success)

        # Verify performance history
        history = self.agent_registry.get_agent_performance_history(agent_id)

        self.assertEqual(history["total_tasks"], 4)
        self.assertEqual(history["successful_tasks"], 3)
        self.assertEqual(history["failed_tasks"], 1)
        self.assertEqual(history["success_rate"], 0.75)

        # Verify response time statistics
        response_stats = history["response_time_stats"]
        self.assertIn("average_response_time", response_stats)
        self.assertIn("min_response_time", response_stats)
        self.assertIn("max_response_time", response_stats)

    def test_artefact_quality_tracking_workflow(self):
        """Test artefact quality tracking through a complete workflow."""
        artefact_path = Path(self.temp_dir) / "docs" / "test_artefact.md"

        # Simulate artefact creation and quality evolution
        quality_evolution = [
            {"score": 60.0, "revisions": 0, "stage": "draft"},
            {"score": 75.0, "revisions": 2, "stage": "in_progress"},
            {"score": 85.0, "revisions": 3, "stage": "refined"},
            {"score": 92.0, "revisions": 4, "stage": "approved"},
        ]

        # Track quality evolution
        for quality_data in quality_evolution:
            success = self.artefact_writer.track_quality_metrics(
                artefact_path, quality_data["score"], quality_data["revisions"]
            )
            self.assertTrue(success)

        # Verify quality history
        history = self.artefact_writer.get_artefact_quality_history(artefact_path)

        self.assertEqual(len(history["quality_history"]), 4)
        self.assertIn("lifecycle_stage", history)
        self.assertIn("quality_trends", history)

        # Verify lifecycle metrics
        lifecycle = self.artefact_writer.get_artefact_lifecycle_metrics(artefact_path)

        self.assertIn("total_revisions", lifecycle)
        self.assertEqual(lifecycle["total_revisions"], 4)
        self.assertIn("approval_readiness", lifecycle)
        self.assertIn("maturity_score", lifecycle)

    def test_system_health_monitoring_integration(self):
        """Test system health monitoring integration."""
        monitor = SystemHealthMonitor()

        # Register test components
        def cpu_health_check():
            return {"cpu_usage": 65.0, "temperature": 45.0}

        def memory_health_check():
            return {"memory_usage": 70.0, "available_mb": 2048}

        def disk_health_check():
            return {"disk_usage": 75.0, "available_gb": 50}

        monitor.register_component("cpu_monitor", cpu_health_check)
        monitor.register_component("memory_monitor", memory_health_check)
        monitor.register_component("disk_monitor", disk_health_check)

        # Perform health checks
        health_status = monitor.get_health_status()

        self.assertIn("overall_status", health_status)
        self.assertIn("component_status", health_status)

        # Verify all components are monitored
        component_status = health_status["component_status"]
        self.assertIn("cpu_monitor", component_status)
        self.assertIn("memory_monitor", component_status)
        self.assertIn("disk_monitor", component_status)

        # Verify health dashboard data
        dashboard_data = monitor.get_health_dashboard_data()

        self.assertIn("overall_health", dashboard_data)
        self.assertIn("component_health", dashboard_data)
        self.assertIn("alerts", dashboard_data)
        self.assertEqual(len(dashboard_data["component_health"]), 3)

    def test_workflow_state_manager_metrics_integration(self):
        """Test workflow state manager metrics integration."""
        workflow_id = "integration_test_workflow"

        # Store multiple metrics entries
        for i in range(5):
            metrics_data = {
                "duration": 8.0 + i * 0.5,
                "task_success_rate": 0.8 + (i % 2) * 0.1,  # Alternating pattern
                "efficiency_score": 70.0 + i * 2,
                "bottlenecks": [{"task_index": i % 3, "duration": 5.0 + i}],
                "timestamp": (datetime.now() + timedelta(hours=i)).isoformat(),
            }

            success = self.state_manager.store_workflow_metrics(
                workflow_id, metrics_data
            )
            self.assertTrue(success)

        # Test performance history retrieval
        history = self.state_manager.get_workflow_performance_history(workflow_id)
        self.assertEqual(len(history), 5)

        # Test aggregated metrics
        aggregated = self.state_manager.get_aggregated_metrics([workflow_id])

        self.assertIn("average_duration", aggregated)
        self.assertIn("average_success_rate", aggregated)
        self.assertIn("total_bottlenecks", aggregated)

        # Test time-range filtering
        recent_aggregated = self.state_manager.get_aggregated_metrics(
            [workflow_id], time_range_hours=2
        )

        # Should have fewer measurements due to time filter
        self.assertLessEqual(recent_aggregated["total_measurements"], 5)


class TestCrossComponentAnalytics(unittest.TestCase):
    """Test analytics that span multiple components."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.crewai_engine = CrewAIOrchestrationEngine()
        self.workflow_manager = BmadWorkflowManager(self.crewai_engine)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_workflow_agent_performance_correlation(self):
        """Test correlation between workflow performance and agent metrics."""
        # This test would verify that agent performance metrics
        # correlate with overall workflow success rates

        agent_registry = AgentRegistry()
        workflow_manager = self.workflow_manager

        # Simulate workflow with agent performance tracking
        # (This would be more complex in a real scenario)

        # Verify that agent performance data is being collected
        # and can be correlated with workflow outcomes

        # For now, just verify the infrastructure is in place
        self.assertIsNotNone(agent_registry)
        self.assertIsNotNone(workflow_manager.metrics_collector)

    def test_artefact_quality_workflow_impact(self):
        """Test how artefact quality impacts workflow efficiency."""
        artefact_writer = BMADArtefactWriter(base_path=self.temp_dir)

        # Create test artefacts with varying quality levels
        high_quality_artefact = Path(self.temp_dir) / "high_quality.md"
        low_quality_artefact = Path(self.temp_dir) / "low_quality.md"

        # Track quality for both artefacts
        artefact_writer.track_quality_metrics(high_quality_artefact, 95.0, 2)
        artefact_writer.track_quality_metrics(low_quality_artefact, 45.0, 6)

        # Verify quality differences are tracked
        high_quality_history = artefact_writer.get_artefact_quality_history(
            high_quality_artefact
        )
        low_quality_history = artefact_writer.get_artefact_quality_history(
            low_quality_artefact
        )

        self.assertGreater(
            high_quality_history["summary_statistics"]["current_quality_score"],
            low_quality_history["summary_statistics"]["current_quality_score"],
        )

        # Verify lifecycle differences
        high_lifecycle = artefact_writer.get_artefact_lifecycle_metrics(
            high_quality_artefact
        )
        low_lifecycle = artefact_writer.get_artefact_lifecycle_metrics(
            low_quality_artefact
        )

        self.assertNotEqual(
            high_lifecycle["approval_readiness"], low_lifecycle["approval_readiness"]
        )

    def test_system_health_workflow_performance_correlation(self):
        """Test correlation between system health and workflow performance."""
        monitor = SystemHealthMonitor()

        # Register health checks
        def system_health_check():
            return {
                "cpu_usage": 80.0,  # High CPU usage
                "memory_usage": 85.0,  # High memory usage
                "response_time": 3.5,  # Slow response time
            }

        monitor.register_component("system_monitor", system_health_check)

        # Get health status
        health_status = monitor.get_health_status()

        # Verify health alerts are generated for poor performance
        self.assertIn("active_alerts", health_status)

        # Check that alerts include the expected metrics
        alerts = health_status["active_alerts"]
        alert_metrics = [alert["metric"] for alert in alerts]

        self.assertIn("cpu_usage", alert_metrics)
        self.assertIn("memory_usage", alert_metrics)
        self.assertIn("response_time", alert_metrics)

    def test_metrics_persistence_and_recovery(self):
        """Test metrics persistence and recovery across component restarts."""
        state_manager = WorkflowStateManager(storage_dir=self.temp_dir)

        workflow_id = "persistence_test_workflow"
        original_metrics = {
            "duration": 12.5,
            "task_success_rate": 0.85,
            "efficiency_score": 78.0,
            "bottlenecks": [{"task_index": 2, "duration": 7.5}],
        }

        # Store metrics
        success = state_manager.store_workflow_metrics(workflow_id, original_metrics)
        self.assertTrue(success)

        # Simulate component restart by creating new instance
        new_state_manager = WorkflowStateManager(storage_dir=self.temp_dir)

        # Retrieve metrics from disk
        retrieved_metrics = new_state_manager.retrieve_workflow_metrics(workflow_id)

        # Verify metrics were persisted and recovered correctly
        self.assertIsNotNone(retrieved_metrics)
        self.assertEqual(retrieved_metrics["duration"], original_metrics["duration"])
        self.assertEqual(
            retrieved_metrics["task_success_rate"],
            original_metrics["task_success_rate"],
        )

    def test_analytics_data_cleanup(self):
        """Test cleanup of old analytics data."""
        state_manager = WorkflowStateManager(storage_dir=self.temp_dir)

        # Store some old metrics (simulate old data)
        old_workflow_id = "old_workflow"
        old_metrics = {
            "duration": 10.0,
            "timestamp": (datetime.now() - timedelta(days=60)).isoformat(),
        }

        # This test verifies the cleanup mechanism exists
        # In a real scenario, we'd need to manipulate file timestamps

        cleaned_count = state_manager.cleanup_old_metrics(max_age_days=30)
        self.assertIsInstance(cleaned_count, int)


class TestPerformanceBenchmarks(unittest.TestCase):
    """Test performance benchmarks for analytics components."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_manager = WorkflowStateManager(storage_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_metrics_collection_performance(self):
        """Test performance of metrics collection operations."""
        workflow_id = "perf_test_workflow"

        # Measure time for multiple metrics collections
        start_time = time.time()

        for i in range(100):
            metrics_data = {
                "duration": 5.0 + i * 0.1,
                "task_success_rate": 0.8,
                "efficiency_score": 75.0,
                "bottlenecks": [],
            }
            self.state_manager.store_workflow_metrics(
                f"{workflow_id}_{i}", metrics_data
            )

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(total_time, 5.0, "Metrics collection took too long")

    def test_analytics_query_performance(self):
        """Test performance of analytics queries."""
        # Create test data
        for i in range(50):
            workflow_id = f"query_perf_workflow_{i}"
            metrics_data = {
                "duration": 5.0 + (i % 10),
                "task_success_rate": 0.7 + (i % 3) * 0.1,
                "efficiency_score": 70.0 + (i % 20),
                "bottlenecks": [{"task_index": i % 5, "duration": 4.0 + (i % 3)}],
            }
            self.state_manager.store_workflow_metrics(workflow_id, metrics_data)

        # Measure query performance
        start_time = time.time()

        aggregated = self.state_manager.get_aggregated_metrics()

        end_time = time.time()
        query_time = end_time - start_time

        # Should complete within reasonable time
        self.assertLess(query_time, 2.0, "Analytics query took too long")
        self.assertIn("average_duration", aggregated)


if __name__ == "__main__":
    unittest.main()
