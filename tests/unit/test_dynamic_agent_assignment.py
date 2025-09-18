"""
Unit tests for dynamic agent assignment functionality.
"""

import logging
import unittest
from unittest.mock import MagicMock, Mock, patch

from src.bmad_crewai.agent_registry import AgentRegistry
from src.bmad_crewai.crewai_engine import BmadWorkflowEngine


class TestDynamicAgentAssignment(unittest.TestCase):
    """Test cases for dynamic agent assignment."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger(__name__)
        self.registry = AgentRegistry()
        self.engine = BmadWorkflowEngine(logger=self.logger)

    def test_get_agent_capabilities_scrum_master(self):
        """Test getting capabilities for scrum master agent."""
        capabilities = self.registry._get_agent_capabilities("scrum-master")
        expected = ["coordination", "process", "facilitation", "agile"]
        self.assertEqual(capabilities, expected)

    def test_get_agent_capabilities_dev_agent(self):
        """Test getting capabilities for dev agent."""
        capabilities = self.registry._get_agent_capabilities("dev-agent")
        expected = ["implementation", "coding", "debugging", "testing"]
        self.assertEqual(capabilities, expected)

    def test_get_agent_capabilities_unknown_agent(self):
        """Test getting capabilities for unknown agent."""
        capabilities = self.registry._get_agent_capabilities("unknown-agent")
        self.assertEqual(capabilities, [])

    def test_score_capability_match_perfect_match(self):
        """Test capability matching with perfect match."""
        task_requirements = {"capabilities": ["implementation", "coding"]}
        score = self.registry._score_capability_match("dev-agent", task_requirements)
        self.assertEqual(score, 1.0)

    def test_score_capability_match_partial_match(self):
        """Test capability matching with partial match."""
        task_requirements = {"capabilities": ["implementation", "design", "testing"]}
        score = self.registry._score_capability_match("dev-agent", task_requirements)
        # dev-agent has implementation, testing but not design
        self.assertEqual(score, 2.0 / 3.0)

    def test_score_capability_match_no_match(self):
        """Test capability matching with no match."""
        task_requirements = {"capabilities": ["design", "architecture"]}
        score = self.registry._score_capability_match("dev-agent", task_requirements)
        self.assertEqual(score, 0.0)

    def test_score_capability_match_no_requirements(self):
        """Test capability matching with no specific requirements."""
        task_requirements = {}
        score = self.registry._score_capability_match("dev-agent", task_requirements)
        self.assertEqual(score, 1.0)

    def test_score_performance_history_with_handoffs(self):
        """Test performance scoring with existing handoffs."""
        # Mock handoff history
        self.registry._agent_handoffs = [
            {"from_agent": "dev-agent", "to_agent": "qa-agent", "error": None},
            {"from_agent": "dev-agent", "to_agent": "architect", "error": None},
        ]

        score = self.registry._score_performance_history("dev-agent", {}, None)
        self.assertEqual(score, 1.0)  # 2 successful handoffs out of 2

    def test_score_performance_history_no_handoffs(self):
        """Test performance scoring with no handoff history."""
        score = self.registry._score_performance_history("dev-agent", {}, None)
        self.assertEqual(score, 0.5)  # Neutral score

    def test_score_load_balance_no_recent_activity(self):
        """Test load balancing with no recent activity."""
        score = self.registry._score_load_balance("dev-agent", None)
        self.assertEqual(score, 1.0)  # Fully available

    def test_score_load_balance_with_activity(self):
        """Test load balancing with recent activity."""
        # Mock recent handoffs
        self.registry._agent_handoffs = [
            {"to_agent": "dev-agent", "timestamp": "recent"},
            {"to_agent": "dev-agent", "timestamp": "recent"},
            {"to_agent": "dev-agent", "timestamp": "recent"},
            {"to_agent": "dev-agent", "timestamp": "recent"},
            {"to_agent": "dev-agent", "timestamp": "recent"},
            {"to_agent": "qa-agent", "timestamp": "recent"},  # Different agent
        ]

        score = self.registry._score_load_balance("dev-agent", None)
        # 5 assignments out of threshold of 5, so load_factor = 1.0, score = 0.0
        self.assertEqual(score, 0.0)

    def test_score_context_compatibility_matching_phase(self):
        """Test context compatibility with matching workflow phase."""
        context = {"phase": "implementation"}
        score = self.registry._score_context_compatibility("dev-agent", context)
        self.assertEqual(score, 1.0)

    def test_score_context_compatibility_no_context(self):
        """Test context compatibility with no context."""
        score = self.registry._score_context_compatibility("dev-agent", None)
        self.assertEqual(score, 1.0)

    def test_score_context_compatibility_partial_match(self):
        """Test context compatibility with partial match."""
        context = {"phase": "unknown_phase"}
        score = self.registry._score_context_compatibility("dev-agent", context)
        self.assertEqual(score, 0.5)  # Partial compatibility

    def test_calculate_agent_score_perfect_match(self):
        """Test overall agent score calculation with perfect match."""
        task_requirements = {"capabilities": ["implementation", "coding"]}
        context = {"phase": "implementation"}
        workflow_id = "test_workflow"

        # Mock handoff history for perfect performance
        self.registry._agent_handoffs = [
            {"from_agent": "dev-agent", "to_agent": "qa-agent", "error": None},
        ]

        score = self.registry._calculate_agent_score(
            "dev-agent", task_requirements, context, workflow_id
        )

        # Should be close to 1.0 (perfect capability match + good performance + good context + available)
        self.assertGreater(score, 0.8)

    def test_calculate_agent_score_poor_match(self):
        """Test overall agent score calculation with poor match."""
        task_requirements = {"capabilities": ["design", "architecture"]}
        context = {"phase": "unknown_phase"}
        workflow_id = "test_workflow"

        # Mock failed handoffs for poor performance
        self.registry._agent_handoffs = [
            {"from_agent": "dev-agent", "to_agent": "qa-agent", "error": "Failed"},
            {"from_agent": "dev-agent", "to_agent": "architect", "error": "Failed"},
        ]

        score = self.registry._calculate_agent_score(
            "dev-agent", task_requirements, context, workflow_id
        )

        # Should be low due to poor capability match and performance
        self.assertLess(score, 0.5)

    @patch("src.bmad_crewai.agent_registry.AgentRegistry._get_available_agents")
    def test_get_optimal_agent_success(self, mock_get_agents):
        """Test successful optimal agent selection."""
        mock_get_agents.return_value = ["dev-agent", "qa-agent", "architect"]

        task_requirements = {"capabilities": ["implementation", "coding"]}
        optimal_agent = self.registry.get_optimal_agent(task_requirements)

        self.assertIsInstance(optimal_agent, str)
        self.assertIn(optimal_agent, ["dev-agent", "qa-agent", "architect"])

    @patch("src.bmad_crewai.agent_registry.AgentRegistry._get_available_agents")
    def test_get_optimal_agent_no_agents(self, mock_get_agents):
        """Test optimal agent selection with no available agents."""
        mock_get_agents.return_value = []

        task_requirements = {"capabilities": ["implementation"]}
        optimal_agent = self.registry.get_optimal_agent(task_requirements)

        self.assertIsNone(optimal_agent)

    def test_extract_task_requirements_implementation_task(self):
        """Test task requirements extraction for implementation task."""
        task_spec = {
            "description": "Implement user authentication feature with proper error handling"
        }
        context = {}

        requirements = self.engine._extract_task_requirements(task_spec, context)

        self.assertIn("implementation", requirements["capabilities"])
        self.assertIn("coding", requirements["capabilities"])
        self.assertEqual(requirements["complexity"], "medium")

    def test_extract_task_requirements_testing_task(self):
        """Test task requirements extraction for testing task."""
        task_spec = {
            "description": "Write comprehensive unit tests for the authentication module"
        }
        context = {}

        requirements = self.engine._extract_task_requirements(task_spec, context)

        self.assertIn("testing", requirements["capabilities"])
        self.assertIn("validation", requirements["capabilities"])

    def test_extract_task_requirements_complex_task(self):
        """Test task requirements extraction for complex task."""
        task_spec = {
            "description": "Design and implement a complex distributed caching system"
        }
        context = {}

        requirements = self.engine._extract_task_requirements(task_spec, context)

        self.assertIn("implementation", requirements["capabilities"])
        self.assertIn("design", requirements["capabilities"])
        self.assertEqual(requirements["complexity"], "high")

    def test_extract_task_requirements_simple_task(self):
        """Test task requirements extraction for simple task."""
        task_spec = {
            "description": "Add a simple logging statement to track user actions"
        }
        context = {}

        requirements = self.engine._extract_task_requirements(task_spec, context)

        self.assertEqual(requirements["complexity"], "low")

    def test_extract_task_requirements_with_priority(self):
        """Test task requirements extraction with priority."""
        task_spec = {
            "description": "Fix critical security vulnerability in authentication",
            "priority": "high",
        }
        context = {}

        requirements = self.engine._extract_task_requirements(task_spec, context)

        self.assertEqual(requirements["priority"], "high")

    def test_extract_task_requirements_with_duration(self):
        """Test task requirements extraction with estimated duration."""
        task_spec = {
            "description": "Refactor entire codebase for better maintainability",
            "estimated_hours": 16,  # Over 8 hours = long
        }
        context = {}

        requirements = self.engine._extract_task_requirements(task_spec, context)

        self.assertEqual(requirements["estimated_duration"], "long")

    def test_fallback_agent_assignment_implementation_task(self):
        """Test fallback agent assignment for implementation task."""
        task_spec = {"description": "Implement new feature for user dashboard"}
        context = {}

        agent = self.engine._fallback_agent_assignment(task_spec, 0, context)
        self.assertEqual(agent, "dev-agent")

    def test_fallback_agent_assignment_testing_task(self):
        """Test fallback agent assignment for testing task."""
        task_spec = {"description": "Write unit tests for the dashboard component"}
        context = {}

        agent = self.engine._fallback_agent_assignment(task_spec, 0, context)
        self.assertEqual(agent, "qa-agent")

    def test_fallback_agent_assignment_design_task(self):
        """Test fallback agent assignment for design task."""
        task_spec = {"description": "Design the architecture for the new microservice"}
        context = {}

        agent = self.engine._fallback_agent_assignment(task_spec, 0, context)
        self.assertEqual(agent, "architect")

    def test_fallback_agent_assignment_coordination_task(self):
        """Test fallback agent assignment for coordination task."""
        task_spec = {"description": "Coordinate the deployment of the new feature"}
        context = {}

        agent = self.engine._fallback_agent_assignment(task_spec, 0, context)
        self.assertEqual(agent, "scrum-master")


if __name__ == "__main__":
    unittest.main()
