"""
Integration tests for advanced workflow orchestration functionality.
"""

import logging
import time
import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from src.bmad_crewai.agent_registry import AgentRegistry
from src.bmad_crewai.artefact_manager import ArtefactManager
from src.bmad_crewai.crewai_engine import BmadWorkflowEngine, CrewAIOrchestrationEngine
from src.bmad_crewai.workflow_state_manager import WorkflowStateManager
from src.bmad_crewai.workflow_visualizer import WorkflowVisualizer


class TestAdvancedWorkflowIntegration(unittest.TestCase):
    """Integration tests for advanced workflow orchestration."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.crew_engine = CrewAIOrchestrationEngine(logger=self.logger)
        self.state_manager = WorkflowStateManager(logger=self.logger)
        self.artefact_manager = ArtefactManager()
        self.visualizer = WorkflowVisualizer(logger=self.logger)
        self.agent_registry = AgentRegistry()

        # Create the workflow engine with all components
        self.workflow_engine = BmadWorkflowEngine(
            crew=self.crew_engine.crew,
            state_manager=self.state_manager,
            artefact_manager=self.artefact_manager,
            visualizer=self.visualizer,
            logger=self.logger,
        )

    def test_conditional_workflow_execution_end_to_end(self):
        """Test end-to-end conditional workflow execution."""
        # Define a conditional workflow template
        workflow_template = {
            "tasks": [
                {
                    "description": "Check user permissions",
                    "agent": "qa-agent",
                    "condition": {
                        "type": "context_check",
                        "key": "user_role",
                        "operator": "equals",
                        "value": "admin",
                    },
                },
                {"description": "Load admin dashboard", "agent": "dev-agent"},
                {"description": "Load user dashboard", "agent": "dev-agent"},
            ]
        }

        # Test with admin context (should execute first task, skip second)
        context = {"user_role": "admin"}
        result = self.workflow_engine.execute_conditional_workflow(
            workflow_template, context, "conditional_admin_test"
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("conditional_decisions", result)

        # Verify that admin-specific task was executed
        task_results = result.get("task_results", [])
        self.assertTrue(len(task_results) >= 1)

    def test_error_recovery_integration_with_artefact_generation(self):
        """Test error recovery integration with artefact generation pipeline."""
        # Define workflow with retry configuration
        workflow_template = {
            "tasks": [
                {
                    "description": "Generate user report",
                    "agent": "dev-agent",
                    "retry": {"max_attempts": 2, "backoff_seconds": 0.1},
                    "output": {
                        "artefact_type": "report",
                        "content_template": "User Report: {{task_message}}",
                        "params": {"format": "json"},
                    },
                }
            ]
        }

        # Mock a task that fails initially but succeeds on retry
        with patch.object(
            self.workflow_engine, "_execute_single_task_attempt"
        ) as mock_execute:
            # First call fails, second call succeeds
            mock_execute.side_effect = [
                {"status": "failed", "error": "Network timeout", "attempt": 1},
                {
                    "status": "success",
                    "message": "Report generated successfully",
                    "attempt": 2,
                },
            ]

            result = self.workflow_engine.execute_conditional_workflow(
                workflow_template, {}, "recovery_test"
            )

            # Verify recovery worked
            self.assertEqual(result["status"], "success")
            task_results = result.get("task_results", [])
            self.assertTrue(len(task_results) > 0)

            task_result = task_results[0]
            self.assertTrue(task_result.get("recovered", False))
            self.assertEqual(task_result.get("recovery_attempts"), 1)

    def test_dynamic_agent_assignment_with_multiple_agents(self):
        """Test dynamic agent assignment with multiple agent types."""
        # Set up agent registry
        self.agent_registry.register_bmad_agents()

        # Define workflow without specific agent assignments
        workflow_template = {
            "tasks": [
                {
                    "description": "Design new feature architecture",
                    "complexity": "high",
                },
                {
                    "description": "Implement the designed feature",
                    "complexity": "medium",
                },
                {"description": "Test the implemented feature", "complexity": "medium"},
            ]
        }

        # Mock the agent assignment to return different agents
        with patch.object(self.workflow_engine, "_assign_optimal_agent") as mock_assign:
            mock_assign.side_effect = ["architect", "dev-agent", "qa-agent"]

            with patch.object(
                self.workflow_engine, "_execute_single_task_attempt"
            ) as mock_execute:
                mock_execute.return_value = {"status": "success"}

                result = self.workflow_engine.execute_conditional_workflow(
                    workflow_template, {}, "dynamic_agent_test"
                )

                # Verify agents were assigned
                self.assertEqual(result["status"], "success")

                # Verify assignment calls were made
                self.assertEqual(mock_assign.call_count, 3)

    def test_workflow_visualization_and_monitoring_integration(self):
        """Test workflow visualization and monitoring in real scenarios."""
        workflow_template = {
            "tasks": [
                {"description": "Initialize project", "agent": "dev-agent"},
                {"description": "Setup configuration", "agent": "architect"},
                {"description": "Validate setup", "agent": "qa-agent"},
            ]
        }

        # Execute workflow
        result = self.workflow_engine.execute_conditional_workflow(
            workflow_template, {}, "visualization_test"
        )

        # Get workflow state for visualization
        workflow_state = self.state_manager.recover_state("visualization_test")
        self.assertIsNotNone(workflow_state)

        # Test Mermaid diagram generation
        mermaid_diagram = self.visualizer.generate_workflow_diagram(
            "visualization_test", workflow_state, workflow_template, "mermaid"
        )

        self.assertIn("flowchart TD", mermaid_diagram)
        self.assertIn("visualization_test", mermaid_diagram)

        # Test ASCII diagram generation
        ascii_diagram = self.visualizer.generate_workflow_diagram(
            "visualization_test", workflow_state, workflow_template, "ascii"
        )

        self.assertIn("Workflow: visualization_test", ascii_diagram)

        # Test metrics collection
        metrics = self.visualizer.collect_workflow_metrics(
            "visualization_test", workflow_state
        )

        self.assertEqual(metrics["workflow_id"], "visualization_test")
        self.assertIn("task_metrics", metrics)
        self.assertIn("performance_metrics", metrics)

    def test_agent_registry_integration_with_workflow_engine(self):
        """Test agent registry integration with workflow engine."""
        # Register agents
        self.agent_registry.register_bmad_agents()

        # Verify agents are registered
        agents = self.agent_registry.list_bmad_agents()
        self.assertIn("dev-agent", agents)
        self.assertIn("qa-agent", agents)
        self.assertIn("architect", agents)

        # Test agent capability scoring
        dev_capabilities = self.agent_registry._get_agent_capabilities("dev-agent")
        qa_capabilities = self.agent_registry._get_agent_capabilities("qa-agent")

        self.assertIn("implementation", dev_capabilities)
        self.assertIn("testing", qa_capabilities)

        # Test optimal agent selection
        task_requirements = {"capabilities": ["implementation", "coding"]}
        optimal_agent = self.agent_registry.get_optimal_agent(task_requirements)

        self.assertIsNotNone(optimal_agent)
        self.assertEqual(optimal_agent, "dev-agent")

    def test_state_management_integration_with_error_recovery(self):
        """Test state management integration with error recovery."""
        workflow_template = {
            "tasks": [
                {
                    "description": "Process data",
                    "agent": "dev-agent",
                    "retry": {"max_attempts": 2, "backoff_seconds": 0.1},
                }
            ]
        }

        # Execute workflow and check state persistence
        result = self.workflow_engine.execute_conditional_workflow(
            workflow_template, {}, "state_recovery_test"
        )

        # Verify state was persisted
        workflow_state = self.state_manager.recover_state("state_recovery_test")
        self.assertIsNotNone(workflow_state)

        # Check state contains expected fields
        self.assertIn("status", workflow_state)
        self.assertIn("steps_completed", workflow_state)
        self.assertIn("execution_timeline", workflow_state)

        # Test workflow recovery from state
        recovery_result = self.workflow_engine.recover_workflow_from_checkpoint(
            "state_recovery_test"
        )

        if recovery_result:
            self.assertIn("recovered", recovery_result)
            self.assertIn("checkpoint_id", recovery_result)

    def test_artefact_generation_integration_with_workflow(self):
        """Test artefact generation integration with workflow execution."""
        workflow_template = {
            "tasks": [
                {
                    "description": "Generate API documentation",
                    "agent": "dev-agent",
                    "output": {
                        "artefact_type": "documentation",
                        "content_template": "# API Documentation\n\nGenerated: {{timestamp}}\n\nStatus: {{status}}",
                        "params": {"format": "markdown"},
                    },
                }
            ]
        }

        # Mock artefact generation
        with patch.object(
            self.artefact_manager, "generate_comprehensive_artefact"
        ) as mock_generate:
            mock_generate.return_value = True

            with patch.object(
                self.workflow_engine, "_execute_single_task_attempt"
            ) as mock_execute:
                mock_execute.return_value = {
                    "status": "success",
                    "message": "Documentation generated",
                    "task_index": 0,
                }

                result = self.workflow_engine.execute_conditional_workflow(
                    workflow_template, {}, "artefact_test"
                )

                # Verify artefact generation was attempted
                self.assertEqual(result["status"], "success")
                mock_generate.assert_called_once()

    def test_conditional_branching_with_context_evaluation(self):
        """Test conditional branching with complex context evaluation."""
        workflow_template = {
            "tasks": [
                {"description": "Evaluate user access level", "agent": "qa-agent"},
                {
                    "description": "Grant admin permissions",
                    "agent": "dev-agent",
                    "condition": {
                        "type": "context_check",
                        "key": "user_level",
                        "operator": "equals",
                        "value": "admin",
                    },
                },
                {
                    "description": "Grant user permissions",
                    "agent": "dev-agent",
                    "condition": {
                        "type": "context_check",
                        "key": "user_level",
                        "operator": "equals",
                        "value": "user",
                    },
                },
                {"description": "Send welcome email", "agent": "dev-agent"},
            ]
        }

        # Test with admin context
        admin_context = {"user_level": "admin"}
        result = self.workflow_engine.execute_conditional_workflow(
            workflow_template, admin_context, "branching_admin_test"
        )

        self.assertEqual(result["status"], "success")

        # Test with user context
        user_context = {"user_level": "user"}
        result = self.workflow_engine.execute_conditional_workflow(
            workflow_template, user_context, "branching_user_test"
        )

        self.assertEqual(result["status"], "success")

    def test_performance_monitoring_with_large_workflow(self):
        """Test performance monitoring with a larger workflow."""
        # Create a workflow with multiple tasks
        num_tasks = 10
        workflow_template = {
            "tasks": [
                {
                    "description": f"Task {i}",
                    "agent": (
                        "dev-agent"
                        if i % 3 == 0
                        else "qa-agent" if i % 3 == 1 else "architect"
                    ),
                }
                for i in range(num_tasks)
            ]
        }

        # Mock successful execution of all tasks
        with patch.object(
            self.workflow_engine, "_execute_single_task_attempt"
        ) as mock_execute:
            mock_execute.return_value = {"status": "success"}

            start_time = time.time()
            result = self.workflow_engine.execute_conditional_workflow(
                workflow_template, {}, "performance_test"
            )
            end_time = time.time()

            # Verify workflow completed
            self.assertEqual(result["status"], "success")

            # Test performance metrics
            workflow_state = self.state_manager.recover_state("performance_test")
            metrics = self.visualizer.collect_workflow_metrics(
                "performance_test", workflow_state
            )

            # Check that metrics were collected
            self.assertIn("performance_metrics", metrics)
            self.assertIn("task_metrics", metrics)

            # Verify task counts
            task_metrics = metrics["task_metrics"]
            self.assertEqual(task_metrics["total_tasks"], num_tasks)

    def test_monitoring_dashboard_comprehensive_view(self):
        """Test comprehensive monitoring dashboard functionality."""
        workflow_template = {
            "tasks": [
                {"description": "Setup", "agent": "dev-agent"},
                {"description": "Process", "agent": "architect"},
                {"description": "Validate", "agent": "qa-agent"},
            ]
        }

        # Execute workflow
        result = self.workflow_engine.execute_conditional_workflow(
            workflow_template, {}, "dashboard_test"
        )

        # Get monitoring dashboard
        dashboard = self.workflow_engine.get_monitoring_dashboard("dashboard_test")

        # Verify dashboard structure
        self.assertEqual(dashboard["workflow_id"], "dashboard_test")
        self.assertIn("timestamp", dashboard)
        self.assertIn("current_status", dashboard)
        self.assertIn("metrics", dashboard)
        self.assertIn("alerts", dashboard)
        self.assertIn("recommendations", dashboard)

    def test_workflow_data_export_multiple_formats(self):
        """Test exporting workflow data in multiple formats."""
        workflow_template = {
            "tasks": [{"description": "Simple task", "agent": "dev-agent"}]
        }

        # Execute workflow
        result = self.workflow_engine.execute_conditional_workflow(
            workflow_template, {}, "export_test"
        )

        # Export workflow data
        exports = self.workflow_engine.export_workflow_data(
            "export_test", ["mermaid", "ascii", "json", "metrics"]
        )

        # Verify all formats were exported
        self.assertIn("mermaid", exports)
        self.assertIn("ascii", exports)
        self.assertIn("json", exports)
        self.assertIn("metrics", exports)

        # Verify content exists
        for format_name, content in exports.items():
            self.assertIsInstance(content, str)
            self.assertTrue(len(content) > 0)


if __name__ == "__main__":
    unittest.main()
