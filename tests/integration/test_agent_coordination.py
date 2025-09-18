"""
Integration tests for BMAD Agent coordination with CrewAI orchestration.

Tests P0 integration scenarios between AgentRegistry and CrewAI orchestration engine.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.bmad_crewai.agent_registry import AgentRegistry
from src.bmad_crewai.crewai_engine import CrewAIOrchestrationEngine
from src.bmad_crewai.exceptions import BmadCrewAIError


class TestAgentCoordinationIntegration:
    """Integration test suite for BMAD agent coordination."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = AgentRegistry()
        self.engine = CrewAIOrchestrationEngine()

    @patch("src.bmad_crewai.crewai_engine.Agent")
    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_full_bmad_agent_integration_workflow(
        self, mock_registry_agent, mock_engine_agent
    ):
        """Test complete BMAD agent integration workflow from registry to orchestration."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent.backstory = "Test Backstory"
        mock_registry_agent.return_value = mock_agent
        mock_engine_agent.return_value = mock_agent

        # Act - Register agents in registry
        registry_result = self.registry.register_bmad_agents()

        # Act - Integrate registry with orchestration engine
        integration_result = self.engine.integrate_bmad_registry(self.registry)

        # Assert
        assert registry_result is True
        assert integration_result is True
        assert len(self.registry.bmad_agents) == 6
        assert len(self.engine.agents) == 6

        # Verify all BMAD agents are registered
        expected_agents = [
            "scrum-master",
            "product-owner",
            "product-manager",
            "architect",
            "dev-agent",
            "qa-agent",
        ]
        for agent_id in expected_agents:
            assert agent_id in self.registry.bmad_agents
            assert agent_id in self.engine.agents

    @patch("src.bmad_crewai.agent_registry.Agent")
    @patch("src.bmad_crewai.agent_registry.Crew")
    def test_bmad_workflow_execution(self, mock_crew_class, mock_agent_class):
        """Test executing a workflow using BMAD agents."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent.backstory = "Test Backstory"
        mock_agent_class.return_value = mock_agent

        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew

        # Register agents and integrate
        self.registry.register_bmad_agents()
        self.engine.integrate_bmad_registry(self.registry)

        # Create workflow specification
        workflow_spec = {
            "name": "test-workflow",
            "tasks": [
                {
                    "description": "Create product requirements document",
                    "expected_output": "PRD document with requirements",
                    "agent": "product-manager",
                },
                {
                    "description": "Design system architecture",
                    "expected_output": "System architecture diagram",
                    "agent": "architect",
                },
            ],
        }

        # Act
        with patch.object(
            self.engine, "execute_workflow"
        ) as mock_execute, patch.object(
            self.engine, "create_task_from_spec"
        ) as mock_create_task:

            mock_task = Mock()
            mock_create_task.return_value = mock_task

            mock_execute.return_value = {
                "status": "success",
                "result": "Workflow completed",
                "tasks_executed": 2,
            }

            result = self.engine.execute_bmad_workflow(workflow_spec)

        # Assert
        assert result["status"] == "success"
        assert result["tasks_executed"] == 2
        mock_execute.assert_called_once()

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_bmad_agent_communication_validation(self, mock_agent_class):
        """Test BMAD agent communication validation."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent.backstory = "Test Backstory"
        mock_agent_class.return_value = mock_agent

        # Register agents and integrate
        self.registry.register_bmad_agents()
        self.engine.integrate_bmad_registry(self.registry)

        # Act
        validation_result = self.engine.validate_bmad_agent_communication()

        # Assert
        assert validation_result["registry_integrated"] is True
        assert validation_result["agents_available"] is True
        assert validation_result["communication_test"] is True
        assert len(validation_result["errors"]) == 0

    @patch("src.bmad_crewai.agent_registry.Agent")
    @patch("src.bmad_crewai.crewai_engine.Crew")
    def test_crew_initialization_with_bmad_agents(
        self, mock_crew_class, mock_agent_class
    ):
        """Test CrewAI crew initialization with BMAD agents."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent.backstory = "Test Backstory"
        mock_agent_class.return_value = mock_agent

        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew

        # Register agents and integrate
        self.registry.register_bmad_agents()
        self.engine.integrate_bmad_registry(self.registry)

        # Act - Initialize crew
        crew_result = self.engine.initialize_crew(list(self.engine.agents.values()))

        # Assert
        assert crew_result is True
        assert self.engine.crew is not None
        from crewai import Process

        mock_crew_class.assert_called_once_with(
            agents=list(self.engine.agents.values()),
            process=Process.sequential,
            verbose=False,
        )

    def test_integration_without_registry(self):
        """Test engine behavior without BMAD registry integration."""
        # Act & Assert
        with pytest.raises(BmadCrewAIError, match="BMAD registry not integrated"):
            self.engine.execute_bmad_workflow({"tasks": []})

        assert self.engine.get_bmad_agent("test-agent") is None
        assert self.engine.list_bmad_agents() == []

        validation = self.engine.validate_bmad_agent_communication()
        assert validation["registry_integrated"] is False
        assert "not integrated" in validation["errors"][0]

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_agent_registry_status_integration(self, mock_agent_class):
        """Test that registry status is properly integrated."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent.backstory = "Test Backstory"
        mock_agent._executor = Mock()
        mock_agent_class.return_value = mock_agent

        # Register some agents
        self.registry.register_product_manager_agent()
        self.registry.register_developer_agent()

        # Integrate with engine
        self.engine.integrate_bmad_registry(self.registry)

        # Act
        registry_status = self.registry.get_registration_status()
        engine_status = self.engine.get_engine_status()

        # Assert
        assert registry_status["total_agents"] == 2
        assert registry_status["registration_complete"] is False
        assert engine_status["agents_registered"] == 2

        # Verify agents are available through both interfaces
        assert "product-manager" in self.registry.bmad_agents
        assert "product-manager" in self.engine.agents
        assert "dev-agent" in self.registry.bmad_agents
        assert "dev-agent" in self.engine.agents

    @patch("src.bmad_crewai.agent_registry.Agent")
    @patch("src.bmad_crewai.agent_registry.Crew")
    def test_workflow_with_invalid_agent_assignment(
        self, mock_crew_class, mock_agent_class
    ):
        """Test workflow execution with invalid agent assignment."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent.backstory = "Test Backstory"
        mock_agent_class.return_value = mock_agent

        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew

        # Register agents and integrate
        self.registry.register_bmad_agents()
        self.engine.integrate_bmad_registry(self.registry)

        # Create workflow with invalid agent
        workflow_spec = {
            "name": "test-workflow",
            "tasks": [
                {
                    "description": "Invalid agent task",
                    "expected_output": "Should fail",
                    "agent": "invalid-agent-id",
                }
            ],
        }

        # Act
        with patch.object(
            self.engine, "execute_workflow"
        ) as mock_execute, patch.object(
            self.engine, "create_task_from_spec"
        ) as mock_create_task:

            mock_create_task.return_value = None  # Invalid agent returns None

            mock_execute.return_value = {
                "status": "success",
                "result": "Partial workflow completed",
                "tasks_executed": 0,  # No valid tasks
            }

            result = self.engine.execute_bmad_workflow(workflow_spec)

        # Assert - Should fail when no valid tasks are found
        assert result["status"] == "error"
        assert "No valid tasks found" in result["error"]

    def test_engine_reset_clears_bmad_integration(self):
        """Test that engine reset clears BMAD registry integration."""
        # Arrange - Mock a registry
        mock_registry = Mock()
        mock_registry.bmad_agents = {"test-agent": Mock()}
        self.engine.bmad_registry = mock_registry
        self.engine.agents = {"test-agent": Mock()}

        # Act
        reset_result = self.engine.reset_engine()

        # Assert
        assert reset_result is True
        assert self.engine.bmad_registry is None
        assert len(self.engine.agents) == 0
        assert self.engine.crew is None

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_agent_validation_integration(self, mock_agent_class):
        """Test agent validation works through integration."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent.backstory = "Test Backstory"
        mock_agent._executor = Mock()
        mock_agent_class.return_value = mock_agent

        # Register agent
        self.registry.register_product_manager_agent()

        # Act - Validate through registry
        registry_validation = self.registry.validate_agent_registration(
            "product-manager"
        )

        # Act - Check through engine after integration
        self.engine.integrate_bmad_registry(self.registry)
        engine_agent = self.engine.get_bmad_agent("product-manager")

        # Assert
        assert registry_validation["registered"] is True
        assert registry_validation["has_required_attributes"] is True
        assert registry_validation["crewai_compatible"] is True
        assert engine_agent is not None
        assert engine_agent.role == "Test Role"
