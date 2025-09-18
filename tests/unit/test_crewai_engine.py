"""
Unit tests for CrewAI Orchestration Engine

Tests P0 scenarios for CrewAI engine initialization, agent management,
and workflow execution.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.bmad_crewai.crewai_engine import CrewAIOrchestrationEngine
from src.bmad_crewai.exceptions import BmadCrewAIError


class TestCrewAIOrchestrationEngine:
    """Test suite for CrewAIOrchestrationEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = CrewAIOrchestrationEngine()

    def test_initialization_with_crewai_available(self):
        """Test successful initialization when CrewAI is available."""
        # Act
        engine = CrewAIOrchestrationEngine()

        # Assert
        assert engine.crewai_version == "0.186.1"  # Should match installed version
        assert engine.crew is None
        assert engine.agents == {}
        assert hasattr(engine, "get_engine_status")

    @patch.dict("sys.modules", {"crewai": None})
    def test_initialization_without_crewai_raises_error(self):
        """Test error handling when CrewAI is not available."""
        # Act & Assert
        with pytest.raises(BmadCrewAIError, match="CrewAI not available"):
            CrewAIOrchestrationEngine()

    def test_get_engine_status_initial(self):
        """Test engine status reporting with no crew initialized."""
        # Act
        status = self.engine.get_engine_status()

        # Assert
        assert status["crewai_version"] == self.engine.crewai_version
        assert status["crew_initialized"] is False
        assert status["agents_registered"] == 0
        assert status["workflows_available"] == 0
        assert status["agent_ids"] == []

    @patch("src.bmad_crewai.crewai_engine.Agent")
    def test_agent_registration_success(self, mock_agent_class):
        """Test successful agent registration."""
        # Arrange
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Act
        result = self.engine.register_agent("test-agent", mock_agent)

        # Assert
        assert result is True
        assert "test-agent" in self.engine.agents
        assert self.engine.agents["test-agent"] == mock_agent

    def test_agent_registration_failure(self):
        """Test agent registration failure with invalid agent."""
        # Act
        result = self.engine.register_agent("test-agent", None)

        # Assert
        assert result is False
        assert "test-agent" not in self.engine.agents

    def test_get_agent_existing(self):
        """Test retrieving existing registered agent."""
        # Arrange
        mock_agent = Mock()
        self.engine.agents["test-agent"] = mock_agent

        # Act
        agent = self.engine.get_agent("test-agent")

        # Assert
        assert agent == mock_agent

    def test_get_agent_nonexistent(self):
        """Test retrieving non-existent agent returns None."""
        # Act
        agent = self.engine.get_agent("nonexistent-agent")

        # Assert
        assert agent is None

    def test_list_agents_empty(self):
        """Test listing agents when none are registered."""
        # Act
        agents = self.engine.list_agents()

        # Assert
        assert agents == []

    def test_list_agents_with_registered(self):
        """Test listing agents when some are registered."""
        # Arrange
        self.engine.agents = {"agent1": Mock(), "agent2": Mock(), "agent3": Mock()}

        # Act
        agents = self.engine.list_agents()

        # Assert
        assert len(agents) == 3
        assert "agent1" in agents
        assert "agent2" in agents
        assert "agent3" in agents

    @patch("src.bmad_crewai.crewai_engine.Crew")
    @patch("src.bmad_crewai.crewai_engine.Process")
    def test_initialize_crew_success(self, mock_process, mock_crew_class):
        """Test successful crew initialization."""
        # Arrange
        mock_crew = Mock()
        mock_crew_class.return_value = mock_crew
        mock_process.SEQUENTIAL = "sequential"

        mock_agent1 = Mock()
        mock_agent2 = Mock()
        self.engine.agents = {"agent1": mock_agent1, "agent2": mock_agent2}

        # Act
        result = self.engine.initialize_crew([mock_agent1, mock_agent2])

        # Assert
        assert result is True
        assert self.engine.crew == mock_crew
        mock_crew_class.assert_called_once_with(
            agents=[mock_agent1, mock_agent2], process="sequential", verbose=False
        )

    def test_initialize_crew_no_agents(self):
        """Test crew initialization failure with no agents."""
        # Act
        result = self.engine.initialize_crew([])

        # Assert
        assert result is False
        assert self.engine.crew is None

    @patch("src.bmad_crewai.crewai_engine.Task")
    def test_create_task_from_spec_valid(self, mock_task_class):
        """Test creating task from valid specification."""
        # Arrange
        mock_task = Mock()
        mock_task_class.return_value = mock_task

        task_spec = {
            "description": "Test task description",
            "expected_output": "Test expected output",
            "agent": "test-agent",
        }

        mock_agent = Mock()
        self.engine.agents = {"test-agent": mock_agent}

        # Act
        result = self.engine.create_task_from_spec(task_spec)

        # Assert
        assert result == mock_task
        mock_task_class.assert_called_once_with(
            description="Test task description",
            expected_output="Test expected output",
            agent=mock_agent,
            context=None,
            tools=[],
        )

    def test_create_task_from_spec_missing_description(self):
        """Test task creation failure with missing description."""
        # Arrange
        task_spec = {"expected_output": "Test output"}

        # Act & Assert
        with pytest.raises(
            BmadCrewAIError, match="Task specification missing 'description'"
        ):
            self.engine.create_task_from_spec(task_spec)

    def test_create_task_from_spec_missing_expected_output(self):
        """Test task creation failure with missing expected output."""
        # Arrange
        task_spec = {"description": "Test description"}

        # Act & Assert
        with pytest.raises(
            BmadCrewAIError, match="Task specification missing 'expected_output'"
        ):
            self.engine.create_task_from_spec(task_spec)

    def test_reset_engine(self):
        """Test engine reset functionality."""
        # Arrange
        self.engine.crew = Mock()
        self.engine.agents = {"test": Mock()}
        self.engine.workflows = {"workflow1": {}}

        # Act
        result = self.engine.reset_engine()

        # Assert
        assert result is True
        assert self.engine.crew is None
        assert self.engine.agents == {}
        assert self.engine.workflows == {}
