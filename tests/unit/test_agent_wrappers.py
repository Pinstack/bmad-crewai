"""
Unit tests for BMAD Agent Wrappers

Tests P0 scenarios for agent wrapper functionality, tool creation,
and CrewAI agent conversion.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.bmad_crewai.agent_wrappers import BmadAgentRegistry, BmadAgentWrapper
from src.bmad_crewai.exceptions import BmadCrewAIError


class TestBmadAgentWrapper:
    """Test suite for BmadAgentWrapper."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent_config = {
            "name": "Test Agent",
            "role": "Test Role",
            "goal": "Test Goal",
            "backstory": "Test Backstory",
            "capabilities": ["create-prd", "validate-requirements"],
        }

    @patch("src.bmad_crewai.agent_wrappers.tool")
    def test_initialization_with_capabilities(self, mock_tool):
        """Test wrapper initialization with capabilities."""
        # Arrange
        mock_tool_instance = Mock()
        mock_tool.return_value = mock_tool_instance

        # Act
        wrapper = BmadAgentWrapper("test-agent", self.agent_config)

        # Assert
        assert wrapper.agent_id == "test-agent"
        assert wrapper.name == "Test Agent"
        assert wrapper.role == "Test Role"
        assert wrapper.goal == "Test Goal"
        assert wrapper.backstory == "Test Backstory"
        assert "create-prd" in wrapper.capabilities
        assert "validate-requirements" in wrapper.capabilities
        assert len(wrapper.tools) == 2  # Two capabilities = two tools

    def test_get_capabilities(self):
        """Test getting agent capabilities."""
        # Arrange
        wrapper = BmadAgentWrapper("test-agent", self.agent_config)

        # Act
        capabilities = wrapper.get_capabilities()

        # Assert
        assert "create-prd" in capabilities
        assert "validate-requirements" in capabilities
        assert len(capabilities) == 2

    def test_has_capability_existing(self):
        """Test checking for existing capability."""
        # Arrange
        wrapper = BmadAgentWrapper("test-agent", self.agent_config)

        # Act & Assert
        assert wrapper.has_capability("create-prd") is True
        assert wrapper.has_capability("validate-requirements") is True

    def test_has_capability_nonexistent(self):
        """Test checking for non-existent capability."""
        # Arrange
        wrapper = BmadAgentWrapper("test-agent", self.agent_config)

        # Act & Assert
        assert wrapper.has_capability("nonexistent-capability") is False

    def test_add_capability_new(self):
        """Test adding a new capability."""
        # Arrange
        wrapper = BmadAgentWrapper("test-agent", self.agent_config)

        # Act
        result = wrapper.add_capability("new-capability")

        # Assert
        assert result is True
        assert wrapper.has_capability("new-capability") is True
        assert len(wrapper.capabilities) == 3

    def test_add_capability_existing(self):
        """Test adding an existing capability returns False."""
        # Arrange
        wrapper = BmadAgentWrapper("test-agent", self.agent_config)

        # Act
        result = wrapper.add_capability("create-prd")

        # Assert
        assert result is False
        assert len(wrapper.capabilities) == 2  # No change

    def test_remove_capability_existing(self):
        """Test removing an existing capability."""
        # Arrange
        wrapper = BmadAgentWrapper("test-agent", self.agent_config)

        # Act
        result = wrapper.remove_capability("create-prd")

        # Assert
        assert result is True
        assert wrapper.has_capability("create-prd") is False
        assert len(wrapper.capabilities) == 1

    def test_remove_capability_nonexistent(self):
        """Test removing a non-existent capability returns False."""
        # Arrange
        wrapper = BmadAgentWrapper("test-agent", self.agent_config)

        # Act
        result = wrapper.remove_capability("nonexistent-capability")

        # Assert
        assert result is False
        assert len(wrapper.capabilities) == 2  # No change

    @patch("src.bmad_crewai.agent_wrappers.Agent")
    def test_to_crewai_agent_success(self, mock_agent_class):
        """Test successful conversion to CrewAI agent."""
        # Arrange
        mock_crewai_agent = Mock()
        mock_agent_class.return_value = mock_crewai_agent
        wrapper = BmadAgentWrapper("test-agent", self.agent_config)

        # Act
        result = wrapper.to_crewai_agent()

        # Assert
        assert result == mock_crewai_agent
        mock_agent_class.assert_called_once_with(
            role="Test Role",
            goal="Test Goal",
            backstory="Test Backstory",
            tools=wrapper.tools,
            allow_delegation=False,
            verbose=False,
        )

    @patch("src.bmad_crewai.agent_wrappers.Agent")
    def test_to_crewai_agent_with_delegation(self, mock_agent_class):
        """Test CrewAI agent creation with delegation enabled."""
        # Arrange
        mock_crewai_agent = Mock()
        mock_agent_class.return_value = mock_crewai_agent
        wrapper = BmadAgentWrapper("test-agent", self.agent_config)

        # Act
        result = wrapper.to_crewai_agent(allow_delegation=True, verbose=True)

        # Assert
        mock_agent_class.assert_called_once_with(
            role="Test Role",
            goal="Test Goal",
            backstory="Test Backstory",
            tools=wrapper.tools,
            allow_delegation=True,
            verbose=True,
        )


class TestBmadAgentRegistry:
    """Test suite for BmadAgentRegistry."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = BmadAgentRegistry()

    @patch("src.bmad_crewai.agent_wrappers.BmadAgentWrapper")
    @patch("src.bmad_crewai.agent_wrappers.Agent")
    def test_register_bmad_agent_success(self, mock_agent_class, mock_wrapper_class):
        """Test successful BMAD agent registration."""
        # Arrange
        mock_wrapper = Mock()
        mock_wrapper.to_crewai_agent.return_value = Mock()
        mock_wrapper_class.return_value = mock_wrapper

        agent_config = {"name": "Test Agent", "role": "Test Role"}

        # Act
        result = self.registry.register_bmad_agent("test-agent", agent_config)

        # Assert
        assert result is True
        assert "test-agent" in self.registry.wrappers
        assert "test-agent" in self.registry.crewai_agents
        mock_wrapper_class.assert_called_once_with(
            "test-agent", agent_config, self.registry.logger
        )

    @patch("src.bmad_crewai.agent_wrappers.BmadAgentWrapper")
    def test_register_bmad_agent_failure(self, mock_wrapper_class):
        """Test BMAD agent registration failure."""
        # Arrange
        mock_wrapper_class.side_effect = Exception("Registration failed")

        # Act
        result = self.registry.register_bmad_agent("test-agent", {})

        # Assert
        assert result is False
        assert "test-agent" not in self.registry.wrappers

    def test_get_wrapper_existing(self):
        """Test getting existing wrapper."""
        # Arrange
        mock_wrapper = Mock()
        self.registry.wrappers["test-agent"] = mock_wrapper

        # Act
        wrapper = self.registry.get_wrapper("test-agent")

        # Assert
        assert wrapper == mock_wrapper

    def test_get_wrapper_nonexistent(self):
        """Test getting non-existent wrapper returns None."""
        # Act
        wrapper = self.registry.get_wrapper("nonexistent-agent")

        # Assert
        assert wrapper is None

    def test_get_crewai_agent_existing(self):
        """Test getting existing CrewAI agent."""
        # Arrange
        mock_agent = Mock()
        self.registry.crewai_agents["test-agent"] = mock_agent

        # Act
        agent = self.registry.get_crewai_agent("test-agent")

        # Assert
        assert agent == mock_agent

    def test_get_crewai_agent_nonexistent(self):
        """Test getting non-existent CrewAI agent returns None."""
        # Act
        agent = self.registry.get_crewai_agent("nonexistent-agent")

        # Assert
        assert agent is None

    def test_list_registered_agents_empty(self):
        """Test listing agents when registry is empty."""
        # Act
        agents = self.registry.list_registered_agents()

        # Assert
        assert agents == []

    def test_list_registered_agents_with_agents(self):
        """Test listing agents when some are registered."""
        # Arrange
        self.registry.wrappers = {"agent1": Mock(), "agent2": Mock()}

        # Act
        agents = self.registry.list_registered_agents()

        # Assert
        assert len(agents) == 2
        assert "agent1" in agents
        assert "agent2" in agents

    def test_get_agents_by_capability(self):
        """Test getting agents by specific capability."""
        # Arrange
        mock_wrapper1 = Mock()
        mock_wrapper1.has_capability.return_value = True
        mock_wrapper2 = Mock()
        mock_wrapper2.has_capability.return_value = False

        self.registry.wrappers = {"agent1": mock_wrapper1, "agent2": mock_wrapper2}

        # Act
        agents = self.registry.get_agents_by_capability("test-capability")

        # Assert
        assert agents == ["agent1"]
        mock_wrapper1.has_capability.assert_called_once_with("test-capability")
        mock_wrapper2.has_capability.assert_called_once_with("test-capability")

    def test_unregister_agent_existing(self):
        """Test unregistering an existing agent."""
        # Arrange
        mock_wrapper = Mock()
        mock_agent = Mock()
        self.registry.wrappers["test-agent"] = mock_wrapper
        self.registry.crewai_agents["test-agent"] = mock_agent

        # Act
        result = self.registry.unregister_agent("test-agent")

        # Assert
        assert result is True
        assert "test-agent" not in self.registry.wrappers
        assert "test-agent" not in self.registry.crewai_agents

    def test_unregister_agent_nonexistent(self):
        """Test unregistering a non-existent agent."""
        # Act
        result = self.registry.unregister_agent("nonexistent-agent")

        # Assert
        assert result is False

    def test_get_registry_status_empty(self):
        """Test registry status when empty."""
        # Act
        status = self.registry.get_registry_status()

        # Assert
        assert status["total_agents"] == 0
        assert status["agent_ids"] == []
        assert status["capabilities"] == []

    def test_get_registry_status_with_agents(self):
        """Test registry status with registered agents."""
        # Arrange
        mock_wrapper = Mock()
        mock_wrapper.get_capabilities.return_value = ["cap1", "cap2"]
        self.registry.wrappers = {"agent1": mock_wrapper}

        # Act
        status = self.registry.get_registry_status()

        # Assert
        assert status["total_agents"] == 1
        assert status["agent_ids"] == ["agent1"]
        assert "cap1" in status["capabilities"]
        assert "cap2" in status["capabilities"]
