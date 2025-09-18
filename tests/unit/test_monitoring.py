"""
Unit tests for monitoring and analytics components.

Tests cover:
- WorkflowMetricsCollector functionality
- SystemHealthMonitor capabilities
- AgentRegistry performance tracking
- ArtefactWriter quality metrics
- WorkflowStateManager metrics storage
"""

import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from src.bmad_crewai.agent_registry import AgentRegistry
from src.bmad_crewai.artefact_writer import BMADArtefactWriter
from src.bmad_crewai.core import SystemHealthMonitor
from src.bmad_crewai.workflow_manager import (
    BmadWorkflowManager,
    WorkflowMetricsCollector,
    WorkflowOptimizer,
)
from src.bmad_crewai.workflow_state_manager import WorkflowStateManager


class TestWorkflowMetricsCollector(unittest.TestCase):
    """Test WorkflowMetricsCollector functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.collector = WorkflowMetricsCollector()

    def test_initialization(self):
        """Test collector initialization."""
        self.assertIsInstance(self.collector.execution_metrics, dict)
        self.assertIsInstance(self.collector.performance_history, dict)
        self.assertEqual(self.collector.bottleneck_threshold, 5.0)

    def test_collect_execution_metrics_success(self):
        """Test successful metrics collection."""
        workflow_id = "test_workflow_001"
        execution_data = {
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(seconds=10)).isoformat(),
            "task_results": {
                "task_0": {
                    "status": "completed",
                    "start_time": datetime.now().isoformat(),
                    "end_time": (datetime.now() + timedelta(seconds=2)).isoformat(),
                },
                "task_1": {
                    "status": "completed",
                    "start_time": datetime.now().isoformat(),
                    "end_time": (datetime.now() + timedelta(seconds=3)).isoformat(),
                },
            },
        }

        result = self.collector.collect_execution_metrics(workflow_id, execution_data)

        self.assertIn("workflow_id", result)
        self.assertIn("duration", result)
        self.assertIn("task_metrics", result)
        self.assertIn("efficiency_metrics", result)
        self.assertEqual(result["workflow_id"], workflow_id)
        self.assertIn(workflow_id, self.collector.execution_metrics)

    def test_analyze_task_performance(self):
        """Test task performance analysis."""
        task_results = {
            "task_0": {
                "status": "completed",
                "start_time": datetime.now().isoformat(),
                "end_time": (datetime.now() + timedelta(seconds=2)).isoformat(),
            },
            "task_1": {
                "status": "failed",
                "start_time": datetime.now().isoformat(),
                "end_time": (datetime.now() + timedelta(seconds=1)).isoformat(),
            },
        }

        result = self.collector._analyze_task_performance(task_results)

        self.assertIn("task_durations", result)
        self.assertIn("average_task_duration", result)
        self.assertIn("task_success_rate", result)
        self.assertEqual(len(result["task_durations"]), 2)
        self.assertEqual(result["task_success_rate"], 0.5)

    def test_identify_bottlenecks(self):
        """Test bottleneck identification."""
        task_metrics = {
            "task_durations": [1.0, 2.0, 8.0, 1.5],  # 8.0s is 4x the average
            "average_task_duration": 3.125,
        }

        bottlenecks = self.collector._identify_bottlenecks(task_metrics)

        self.assertEqual(len(bottlenecks), 1)
        self.assertEqual(bottlenecks[0]["task_index"], 2)
        self.assertEqual(bottlenecks[0]["duration"], 8.0)
        self.assertEqual(bottlenecks[0]["severity"], "high")

    def test_calculate_efficiency_metrics(self):
        """Test efficiency metrics calculation."""
        task_durations = [1.0, 1.1, 1.2, 0.9, 1.3]  # Very consistent

        result = self.collector._calculate_efficiency_metrics(
            {"task_durations": task_durations}
        )

        self.assertIn("efficiency_score", result)
        self.assertIn("variability_coefficient", result)
        self.assertIn("consistency_rating", result)
        self.assertGreater(
            result["efficiency_score"], 90
        )  # Should be very high for consistent data

    def test_get_workflow_performance_trends_insufficient_data(self):
        """Test performance trends with insufficient data."""
        result = self.collector.get_workflow_performance_trends("nonexistent_workflow")
        self.assertTrue(result.get("insufficient_data"))

    def test_get_aggregated_metrics_no_data(self):
        """Test aggregated metrics when no data exists."""
        result = self.collector.get_aggregated_metrics()
        self.assertTrue(result.get("no_data"))


class TestWorkflowOptimizer(unittest.TestCase):
    """Test WorkflowOptimizer functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.optimizer = WorkflowOptimizer()

    def test_generate_recommendations_success_rate_issue(self):
        """Test recommendations for low success rate."""
        metrics_data = {
            "workflow_id": "test_workflow",
            "task_success_rate": 0.5,  # 50% success rate
            "task_metrics": {"average_task_duration": 15.0},  # Long tasks
            "bottlenecks": [],
            "efficiency_metrics": {"efficiency_score": 60.0},
        }

        result = self.optimizer.generate_recommendations(metrics_data)

        self.assertIn("recommendations", result)
        self.assertIn("priority_score", result)
        self.assertGreater(len(result["recommendations"]), 0)

        # Should have reliability improvement recommendation
        reliability_rec = next(
            (
                r
                for r in result["recommendations"]
                if r.get("type") == "reliability_improvement"
            ),
            None,
        )
        self.assertIsNotNone(reliability_rec)

    def test_analyze_bottlenecks_high_severity(self):
        """Test high severity bottleneck analysis."""
        bottlenecks = [
            {
                "severity": "high",
                "duration": 10.0,
                "task_index": 0,
            }
        ]

        recommendations = self.optimizer._analyze_bottlenecks(bottlenecks)

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["type"], "bottleneck_optimization")
        self.assertEqual(recommendations[0]["impact"], "high")
        self.assertEqual(recommendations[0]["priority_score"], 90)

    def test_analyze_efficiency_low_score(self):
        """Test efficiency analysis with low score."""
        efficiency_metrics = {
            "efficiency_score": 40.0,  # Very low
            "variability_coefficient": 0.8,
        }

        recommendations = self.optimizer._analyze_efficiency(efficiency_metrics)

        self.assertGreater(len(recommendations), 0)
        efficiency_rec = recommendations[0]
        self.assertEqual(efficiency_rec["type"], "efficiency_optimization")
        self.assertEqual(efficiency_rec["impact"], "high")

    def test_calculate_optimization_potential(self):
        """Test optimization potential calculation."""
        recommendations = [
            {"impact": "high"},
            {"impact": "medium"},
            {"impact": "low"},
        ]

        potential = self.optimizer._calculate_optimization_potential(recommendations)
        self.assertEqual(potential, "medium")  # 33% high impact


class TestSystemHealthMonitor(unittest.TestCase):
    """Test SystemHealthMonitor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = SystemHealthMonitor()

    def test_initialization(self):
        """Test monitor initialization."""
        self.assertIsInstance(self.monitor.health_indicators, dict)
        self.assertIsInstance(self.monitor.alert_thresholds, dict)
        self.assertIn("cpu_usage", self.monitor.alert_thresholds)
        self.assertIn("memory_usage", self.monitor.alert_thresholds)

    def test_register_component(self):
        """Test component registration."""

        def mock_health_check():
            return {"cpu_usage": 50.0, "memory_usage": 60.0}

        success = self.monitor.register_component(
            "test_component", mock_health_check, {"cpu_usage": 75.0}
        )

        self.assertTrue(success)
        self.assertIn("test_component", self.monitor.health_indicators)

    def test_perform_health_check(self):
        """Test health check execution."""

        def mock_health_check():
            return {"cpu_usage": 85.0, "memory_usage": 70.0}  # CPU over threshold

        self.monitor.register_component("test_component", mock_health_check)

        result = self.monitor.perform_health_check("test_component")

        self.assertIn("overall_status", result)
        self.assertIn("component_results", result)
        self.assertIn("test_component", result["component_results"])

        component_result = result["component_results"]["test_component"]
        self.assertIn("alerts", component_result)
        self.assertGreater(len(component_result["alerts"]), 0)

    def test_assess_health_status_healthy(self):
        """Test health status assessment for healthy metrics."""
        health_data = {"cpu_usage": 50.0, "memory_usage": 60.0}
        thresholds = self.monitor.alert_thresholds

        status = self.monitor._assess_health_status(health_data, thresholds)
        self.assertEqual(status, "healthy")

    def test_assess_health_status_critical(self):
        """Test health status assessment for critical metrics."""
        health_data = {"cpu_usage": 95.0, "memory_usage": 90.0}  # Both over thresholds
        thresholds = self.monitor.alert_thresholds

        status = self.monitor._assess_health_status(health_data, thresholds)
        self.assertEqual(status, "critical")

    def test_get_health_status(self):
        """Test comprehensive health status retrieval."""

        def mock_health_check():
            return {"cpu_usage": 50.0, "memory_usage": 60.0}

        self.monitor.register_component("test_component", mock_health_check)

        status = self.monitor.get_health_status()

        self.assertIn("overall_status", status)
        self.assertIn("component_status", status)
        self.assertIn("health_trends", status)
        self.assertIn("active_alerts", status)
        self.assertIn("system_summary", status)

    def test_clear_alerts(self):
        """Test alert cleanup functionality."""
        # This would test the alert clearing mechanism
        # For now, just verify the method exists and returns an integer
        cleared_count = self.monitor.clear_alerts()
        self.assertIsInstance(cleared_count, int)
        self.assertGreaterEqual(cleared_count, 0)


class TestAgentRegistryPerformance(unittest.TestCase):
    """Test AgentRegistry performance tracking extensions."""

    def setUp(self):
        """Set up test fixtures."""
        self.registry = AgentRegistry()

    def test_track_performance_success(self):
        """Test successful performance tracking."""
        agent_id = "test_agent"
        task_metrics = {
            "success": True,
            "response_time": 2.5,
            "timestamp": datetime.now().isoformat(),
            "task_type": "test_task",
        }

        result = self.registry.track_performance(agent_id, task_metrics)
        self.assertTrue(result)

    def test_track_performance_failure(self):
        """Test performance tracking with failure."""
        agent_id = "test_agent"
        task_metrics = {
            "success": False,
            "response_time": 1.0,
            "timestamp": datetime.now().isoformat(),
            "error_type": "timeout",
        }

        result = self.registry.track_performance(agent_id, task_metrics)
        self.assertTrue(result)

    def test_get_agent_performance_history(self):
        """Test performance history retrieval."""
        agent_id = "test_agent"

        # Add some performance data
        for i in range(3):
            task_metrics = {
                "success": i % 2 == 0,  # Alternate success/failure
                "response_time": 1.0 + i * 0.5,
                "timestamp": datetime.now().isoformat(),
                "task_type": f"task_{i}",
            }
            self.registry.track_performance(agent_id, task_metrics)

        history = self.registry.get_agent_performance_history(agent_id)

        self.assertIn("total_tasks", history)
        self.assertEqual(history["total_tasks"], 3)
        self.assertIn("success_rate", history)
        self.assertIn("response_time_stats", history)
        self.assertIn("performance_score", history)

    def test_get_agent_performance_trends(self):
        """Test performance trend analysis."""
        agent_id = "test_agent"

        # Add performance data with improving trend
        for i in range(5):
            task_metrics = {
                "success": True,
                "response_time": 3.0 - i * 0.2,  # Decreasing response time
                "timestamp": datetime.now().isoformat(),
                "task_type": f"task_{i}",
            }
            self.registry.track_performance(agent_id, task_metrics)

        trends = self.registry.get_agent_performance_trends(agent_id)

        self.assertIn("success_rate_trend", trends)
        self.assertIn("response_time_trend", trends)
        self.assertIn("recommendations", trends)


class TestArtefactWriterQualityMetrics(unittest.TestCase):
    """Test BMADArtefactWriter quality metrics extensions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.writer = BMADArtefactWriter(base_path=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_track_quality_metrics(self):
        """Test quality metrics tracking."""
        artefact_path = Path(self.temp_dir) / "test_artefact.md"
        quality_score = 85.0
        revision_count = 3

        result = self.writer.track_quality_metrics(
            artefact_path, quality_score, revision_count
        )
        self.assertTrue(result)

    def test_get_artefact_quality_history(self):
        """Test quality history retrieval."""
        artefact_path = Path(self.temp_dir) / "test_artefact.md"

        # Track multiple quality updates
        for i in range(3):
            quality_score = 70.0 + i * 10  # 70, 80, 90
            self.writer.track_quality_metrics(artefact_path, quality_score, i + 1)

        history = self.writer.get_artefact_quality_history(artefact_path)

        self.assertIn("quality_history", history)
        self.assertEqual(len(history["quality_history"]), 3)
        self.assertIn("summary_statistics", history)
        self.assertIn("recommendations", history)

    def test_determine_lifecycle_stage(self):
        """Test lifecycle stage determination."""
        # Test with different quality data
        quality_data = {
            "quality_scores": [{"score": 95.0}, {"score": 92.0}],
            "revision_counts": [{"count": 1}, {"count": 2}],
        }

        stage = self.writer._determine_lifecycle_stage(quality_data)
        self.assertEqual(stage, "approved")  # High quality, few revisions

        # Test with low quality and many revisions
        quality_data_low = {
            "quality_scores": [{"score": 45.0}],
            "revision_counts": [{"count": 5}],
        }

        stage_low = self.writer._determine_lifecycle_stage(quality_data_low)
        self.assertEqual(stage_low, "needs_attention")

    def test_get_aggregated_quality_metrics(self):
        """Test aggregated quality metrics."""
        # Add some quality data
        artefact1 = Path(self.temp_dir) / "artefact1.md"
        artefact2 = Path(self.temp_dir) / "artefact2.md"

        self.writer.track_quality_metrics(artefact1, 90.0, 1)
        self.writer.track_quality_metrics(artefact2, 75.0, 3)

        aggregated = self.writer.get_aggregated_quality_metrics()

        self.assertIn("total_artefacts_tracked", aggregated)
        self.assertEqual(aggregated["total_artefacts_tracked"], 2)
        self.assertIn("aggregate_statistics", aggregated)
        self.assertIn("quality_health_score", aggregated)


class TestWorkflowStateManagerMetrics(unittest.TestCase):
    """Test WorkflowStateManager metrics storage extensions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_manager = WorkflowStateManager(storage_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_store_workflow_metrics(self):
        """Test metrics storage."""
        workflow_id = "test_workflow"
        metrics_data = {
            "duration": 10.5,
            "task_success_rate": 0.8,
            "efficiency_score": 75.0,
            "bottlenecks": [{"task_index": 1, "duration": 8.0}],
        }

        result = self.state_manager.store_workflow_metrics(workflow_id, metrics_data)
        self.assertTrue(result)

    def test_retrieve_workflow_metrics(self):
        """Test metrics retrieval."""
        workflow_id = "test_workflow"
        metrics_data = {"duration": 5.0, "success": True}

        # Store metrics
        self.state_manager.store_workflow_metrics(workflow_id, metrics_data)

        # Retrieve metrics
        retrieved = self.state_manager.retrieve_workflow_metrics(workflow_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["duration"], 5.0)

    def test_get_workflow_performance_history(self):
        """Test performance history retrieval."""
        workflow_id = "test_workflow"

        # Store multiple metrics
        for i in range(3):
            metrics_data = {
                "duration": 5.0 + i,
                "task_success_rate": 0.7 + i * 0.1,
                "efficiency_score": 70.0 + i * 5,
                "bottlenecks": [],
            }
            self.state_manager.store_workflow_metrics(workflow_id, metrics_data)

        history = self.state_manager.get_workflow_performance_history(workflow_id)
        self.assertEqual(len(history), 3)

    def test_get_aggregated_metrics(self):
        """Test aggregated metrics calculation."""
        # Store metrics for multiple workflows
        workflows = ["wf1", "wf2", "wf3"]

        for wf_id in workflows:
            metrics_data = {
                "duration": 10.0,
                "task_success_rate": 0.8,
                "efficiency_score": 75.0,
                "bottlenecks": [],
            }
            self.state_manager.store_workflow_metrics(wf_id, metrics_data)

        aggregated = self.state_manager.get_aggregated_metrics()

        self.assertIn("total_workflows", aggregated)
        self.assertEqual(aggregated["total_workflows"], 3)
        self.assertIn("average_duration", aggregated)
        self.assertIn("average_success_rate", aggregated)

    def test_cleanup_old_metrics(self):
        """Test metrics cleanup functionality."""
        # This tests the cleanup mechanism
        cleaned_count = self.state_manager.cleanup_old_metrics(max_age_days=1)
        self.assertIsInstance(cleaned_count, int)
        self.assertGreaterEqual(cleaned_count, 0)


if __name__ == "__main__":
    unittest.main()
