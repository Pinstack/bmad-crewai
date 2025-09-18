"""
Unit tests for BMAD Agent Registry

Tests P0 scenarios for agent registration, validation, and CrewAI integration.
Covers individual agent registration methods, error handling, and coordination testing.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.bmad_crewai.agent_registry import AgentRegistry
from src.bmad_crewai.exceptions import BmadCrewAIError


class TestAgentRegistry:
    """Test suite for AgentRegistry class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = AgentRegistry()

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_bmad_agents_success(self, mock_agent_class):
        """Test successful registration of all BMAD agents."""
        # Arrange
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Act
        result = self.registry.register_bmad_agents()

        # Assert
        assert result is True
        assert len(self.registry.bmad_agents) == 6
        assert "scrum-master" in self.registry.bmad_agents
        assert "product-owner" in self.registry.bmad_agents
        assert "product-manager" in self.registry.bmad_agents
        assert "architect" in self.registry.bmad_agents
        assert "dev-agent" in self.registry.bmad_agents
        assert "qa-agent" in self.registry.bmad_agents

        # Verify Agent constructor was called 6 times
        assert mock_agent_class.call_count == 6

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_bmad_agents_crew_initialization(self, mock_agent_class):
        """Test that CrewAI crew is initialized when agents are registered."""
        # Arrange
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        with patch("src.bmad_crewai.agent_registry.Crew") as mock_crew_class:
            mock_crew = Mock()
            mock_crew_class.return_value = mock_crew

            # Act
            result = self.registry.register_bmad_agents()

            # Assert
            assert result is True
            assert self.registry.crew is not None
            mock_crew_class.assert_called_once_with(
                agents=list(self.registry.bmad_agents.values()), verbose=False
            )

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_bmad_agents_partial_failure(self, mock_agent_class):
        """Test handling of partial registration failures."""
        # Arrange - Make Agent constructor fail on third call
        mock_agent = Mock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:  # Fail on architect registration
                raise Exception("Agent creation failed")
            return mock_agent

        mock_agent_class.side_effect = side_effect

        # Act
        result = self.registry.register_bmad_agents()

        # Assert
        assert result is False  # Should fail due to architect registration failure
        assert len(self.registry.bmad_agents) < 6  # Not all agents registered

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_product_manager_agent(self, mock_agent_class):
        """Test individual Product Manager agent registration."""
        # Arrange
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Act
        result = self.registry.register_product_manager_agent()

        # Assert
        assert result is True
        assert "product-manager" in self.registry.bmad_agents
        mock_agent_class.assert_called_once_with(
            role="Investigative Product Strategist & Market-Savvy PM",
            goal="Creating PRDs and product documentation using templates",
            backstory="Specialized in document creation and product research",
            allow_delegation=False,
            verbose=False,
        )

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_system_architect_agent(self, mock_agent_class):
        """Test individual System Architect agent registration."""
        # Arrange
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Act
        result = self.registry.register_system_architect_agent()

        # Assert
        assert result is True
        assert "architect" in self.registry.bmad_agents
        mock_agent_class.assert_called_once_with(
            role="Holistic System Architect & Full-Stack Technical Leader",
            goal="Complete systems architecture and cross-stack optimization",
            backstory="Master of holistic application design and technology selection",
            allow_delegation=False,
            verbose=False,
        )

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_qa_agent(self, mock_agent_class):
        """Test individual QA agent registration."""
        # Arrange
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Act
        result = self.registry.register_qa_agent()

        # Assert
        assert result is True
        assert "qa-agent" in self.registry.bmad_agents
        mock_agent_class.assert_called_once_with(
            role="Test Architect with Quality Advisory Authority",
            goal="Provide thorough quality assessment and actionable recommendations",
            backstory="Comprehensive quality analysis through test architecture and risk assessment",
            allow_delegation=False,
            verbose=False,
        )

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_developer_agent(self, mock_agent_class):
        """Test individual Developer agent registration."""
        # Arrange
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Act
        result = self.registry.register_developer_agent()

        # Assert
        assert result is True
        assert "dev-agent" in self.registry.bmad_agents
        mock_agent_class.assert_called_once_with(
            role="Expert Senior Software Engineer & Implementation Specialist",
            goal="Execute stories with precision and comprehensive testing",
            backstory="Implements requirements with detailed task execution",
            allow_delegation=False,
            verbose=False,
        )

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_product_owner_agent(self, mock_agent_class):
        """Test individual Product Owner agent registration."""
        # Arrange
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Act
        result = self.registry.register_product_owner_agent()

        # Assert
        assert result is True
        assert "product-owner" in self.registry.bmad_agents
        mock_agent_class.assert_called_once_with(
            role="Technical Product Owner & Process Steward",
            goal="Validate artifacts cohesion and coach significant changes",
            backstory="Guardian of quality and completeness in project artifacts",
            allow_delegation=False,
            verbose=False,
        )

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_scrum_master_agent(self, mock_agent_class):
        """Test individual Scrum Master agent registration."""
        # Arrange
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Act
        result = self.registry.register_scrum_master_agent()

        # Assert
        assert result is True
        assert "scrum-master" in self.registry.bmad_agents
        mock_agent_class.assert_called_once_with(
            role="Technical Scrum Master & Process Steward",
            goal="Ensure agile process adherence and create actionable development tasks",
            backstory="Expert in BMAD methodology, focuses on story creation and process guidance",
            allow_delegation=False,
            verbose=False,
        )

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_single_agent_unknown_id(self, mock_agent_class):
        """Test registration of unknown agent ID."""
        # Act
        result = self.registry._register_single_agent("unknown-agent")

        # Assert
        assert result is False
        mock_agent_class.assert_not_called()

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_register_single_agent_creation_failure(self, mock_agent_class):
        """Test handling of agent creation failure."""
        # Arrange
        mock_agent_class.side_effect = Exception("Agent creation failed")

        # Act
        result = self.registry.register_product_manager_agent()

        # Assert
        assert result is False
        assert "product-manager" not in self.registry.bmad_agents

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_get_bmad_agent_existing(self, mock_agent_class):
        """Test getting an existing registered agent."""
        # Arrange
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        self.registry.register_product_manager_agent()

        # Act
        agent = self.registry.get_bmad_agent("product-manager")

        # Assert
        assert agent is mock_agent

    def test_get_bmad_agent_nonexistent(self):
        """Test getting a non-existent agent."""
        # Act
        agent = self.registry.get_bmad_agent("nonexistent-agent")

        # Assert
        assert agent is None

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_list_bmad_agents(self, mock_agent_class):
        """Test listing all registered agents."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent_class.return_value = mock_agent

        self.registry.register_product_manager_agent()

        # Act
        agent_list = self.registry.list_bmad_agents()

        # Assert
        assert "product-manager" in agent_list
        assert agent_list["product-manager"]["name"] == "Test Role"
        assert agent_list["product-manager"]["goal"] == "Test Goal"
        assert agent_list["product-manager"]["registered"] is True

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_validate_agent_registration_success(self, mock_agent_class):
        """Test successful agent validation."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent.backstory = "Test Backstory"
        mock_agent._executor = Mock()  # Simulate CrewAI compatibility
        mock_agent_class.return_value = mock_agent

        self.registry.register_product_manager_agent()

        # Act
        validation = self.registry.validate_agent_registration("product-manager")

        # Assert
        assert validation["registered"] is True
        assert validation["has_required_attributes"] is True
        assert validation["crewai_compatible"] is True
        assert len(validation["validation_errors"]) == 0

    def test_validate_agent_registration_not_found(self):
        """Test validation of non-existent agent."""
        # Act
        validation = self.registry.validate_agent_registration("nonexistent-agent")

        # Assert
        assert validation["registered"] is False
        assert "not found" in validation["validation_errors"][0]

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_validate_agent_registration_missing_attributes(self, mock_agent_class):
        """Test validation of agent with missing attributes."""
        # Arrange
        mock_agent = Mock()
        # Explicitly remove required attributes from the mock
        del mock_agent.role
        del mock_agent.goal
        del mock_agent.backstory
        mock_agent_class.return_value = mock_agent

        self.registry.register_product_manager_agent()

        # Act
        validation = self.registry.validate_agent_registration("product-manager")

        # Assert
        assert validation["registered"] is True
        assert validation["has_required_attributes"] is False
        assert len(validation["validation_errors"]) == 3  # role, goal, backstory

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_get_registration_status_complete(self, mock_agent_class):
        """Test getting complete registration status."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent.backstory = "Test Backstory"
        mock_agent._executor = Mock()
        mock_agent_class.return_value = mock_agent

        self.registry.register_bmad_agents()

        # Act
        status = self.registry.get_registration_status()

        # Assert
        assert status["total_agents"] == 6
        assert status["expected_agents"] == 6
        assert status["registration_complete"] is True
        assert len(status["agent_status"]) == 6
        assert len(status["errors"]) == 0

    @patch("src.bmad_crewai.agent_registry.Agent")
    def test_get_registration_status_incomplete(self, mock_agent_class):
        """Test getting incomplete registration status."""
        # Arrange - Only register 2 agents instead of all 6
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent.backstory = "Test Backstory"
        mock_agent._executor = Mock()
        mock_agent_class.return_value = mock_agent

        self.registry.register_product_manager_agent()
        self.registry.register_developer_agent()

        # Act
        status = self.registry.get_registration_status()

        # Assert
        assert status["total_agents"] == 2
        assert status["expected_agents"] == 6
        assert status["registration_complete"] is False
        assert len(status["errors"]) == 4  # 4 missing agents

    @patch("src.bmad_crewai.agent_registry.Agent")
    @patch("src.bmad_crewai.agent_registry.Crew")
    def test_test_agent_coordination_success(self, mock_crew_class, mock_agent_class):
        """Test successful agent coordination testing."""
        # Arrange
        mock_agent = Mock()
        mock_agent.role = "Test Role"
        mock_agent.goal = "Test Goal"
        mock_agent_class.return_value = mock_agent

        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew

        self.registry.register_bmad_agents()

        # Act
        results = self.registry.test_agent_coordination()

        # Assert
        assert results["agent_registration"] is True
        assert results["crew_initialization"] is True
        assert results["coordination_test"] is True

    def test_test_agent_coordination_no_agents(self):
        """Test coordination testing with no agents."""
        # Act
        results = self.registry.test_agent_coordination()

        # Assert
        assert results["agent_registration"] is False
        assert results["crew_initialization"] is False
        assert results["coordination_test"] is False

    @patch("src.bmad_crewai.agent_registry.Agent")
    @patch("src.bmad_crewai.agent_registry.Crew")
    def test_test_agent_coordination_missing_attributes(
        self, mock_crew_class, mock_agent_class
    ):
        """Test coordination testing when agent has missing attributes."""
        # Arrange
        mock_agent = Mock()
        # Explicitly remove required attributes from the mock
        del mock_agent.role
        del mock_agent.goal
        mock_agent_class.return_value = mock_agent

        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew

        self.registry.register_bmad_agents()

        # Act
        results = self.registry.test_agent_coordination()

        # Assert
        assert results["agent_registration"] is True
        assert results["crew_initialization"] is True
        assert results["coordination_test"] is False
