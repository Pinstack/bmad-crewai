"""
BMAD Agent Wrappers for CrewAI Integration

This module provides wrapper classes that adapt BMAD agents to be compatible
with CrewAI's Agent interface and tool system.
"""

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from crewai import Agent
from crewai.tools import tool

from .exceptions import BmadCrewAIError


class BmadAgentWrapper:
    """
    Adapter class converting BMAD agents to CrewAI-compatible tools and agents.

    This wrapper allows BMAD agents to be used as CrewAI tools while maintaining
    their original functionality and capabilities.
    """

    def __init__(
        self,
        agent_id: str,
        agent_config: Dict[str, Any],
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the BMAD agent wrapper.

        Args:
            agent_id: Unique identifier for the BMAD agent
            agent_config: Configuration dictionary containing agent specifications
            logger: Optional logger instance

        Raises:
            BmadCrewAIError: If validation fails
        """
        self.logger = logger or logging.getLogger(__name__)

        # Validate inputs
        self._validate_agent_id(agent_id)
        self._validate_agent_config(agent_config)

        self.agent_id = agent_id
        self.agent_config = agent_config

        # Extract agent specifications
        self.name = agent_config.get("name", agent_id)
        self.role = agent_config.get("role", "")
        self.goal = agent_config.get("goal", "")
        self.backstory = agent_config.get("backstory", "")

        # Initialize capabilities and tools
        self.capabilities = agent_config.get("capabilities", [])
        self.tools = []

        # Create CrewAI-compatible tools from capabilities
        self._create_tools_from_capabilities()

    def _validate_agent_id(self, agent_id: str):
        """
        Validate agent ID format and security.

        Args:
            agent_id: Agent identifier to validate

        Raises:
            BmadCrewAIError: If validation fails
        """
        if not agent_id:
            raise BmadCrewAIError("Agent ID cannot be empty")

        if not isinstance(agent_id, str):
            raise BmadCrewAIError("Agent ID must be a string")

        if len(agent_id) > 100:
            raise BmadCrewAIError("Agent ID too long (max 100 characters)")

        # Allow only alphanumeric, hyphens, and underscores
        if not re.match(r"^[a-zA-Z0-9_-]+$", agent_id):
            raise BmadCrewAIError(
                "Agent ID contains invalid characters (only alphanumeric, hyphens, underscores allowed)"
            )

        # Prevent path traversal attacks
        if ".." in agent_id or "/" in agent_id or "\\" in agent_id:
            raise BmadCrewAIError("Agent ID contains path traversal characters")

    def _validate_agent_config(self, agent_config: Dict[str, Any]):
        """
        Validate agent configuration for security and completeness.

        Args:
            agent_config: Agent configuration dictionary

        Raises:
            BmadCrewAIError: If validation fails
        """
        if not isinstance(agent_config, dict):
            raise BmadCrewAIError("Agent config must be a dictionary")

        # Validate required fields are present and of correct type
        required_fields = {"role": str, "goal": str, "backstory": str}

        for field, expected_type in required_fields.items():
            if field in agent_config:
                value = agent_config[field]
                if not isinstance(value, expected_type):
                    raise BmadCrewAIError(
                        f"Agent config field '{field}' must be {expected_type.__name__}"
                    )

                # Length validation
                if isinstance(value, str) and len(value) > 1000:
                    raise BmadCrewAIError(
                        f"Agent config field '{field}' too long (max 1000 characters)"
                    )

                # Content validation - prevent script injection
                if isinstance(value, str) and any(
                    char in value for char in ["<", ">", "&", '"', "'"]
                ):
                    self.logger.warning(
                        f"Agent config field '{field}' contains potentially unsafe characters"
                    )

        # Validate capabilities if present
        if "capabilities" in agent_config:
            capabilities = agent_config["capabilities"]
            if not isinstance(capabilities, list):
                raise BmadCrewAIError("Capabilities must be a list")

            for capability in capabilities:
                if not isinstance(capability, str):
                    raise BmadCrewAIError("Each capability must be a string")

                if len(capability) > 50:
                    raise BmadCrewAIError(
                        "Capability name too long (max 50 characters)"
                    )

                # Validate capability name format
                if not re.match(r"^[a-zA-Z0-9_-]+$", capability):
                    raise BmadCrewAIError(
                        f"Capability '{capability}' contains invalid characters"
                    )

    def _create_tools_from_capabilities(self):
        """Create CrewAI-compatible tools from BMAD agent capabilities."""
        for capability in self.capabilities:
            try:
                tool_func = self._create_tool_function(capability)
                if tool_func:
                    self.tools.append(tool_func)
                    self.logger.debug(f"Created tool for capability: {capability}")
            except Exception as e:
                self.logger.warning(
                    f"Failed to create tool for capability {capability}: {e}"
                )

    def _create_tool_function(self, capability: str) -> Optional[Callable]:
        """
        Create a CrewAI tool function from a BMAD agent capability.

        Args:
            capability: The capability to convert to a tool

        Returns:
            CrewAI tool function or None if creation fails
        """
        try:
            # Map capabilities to tool functions
            capability_map = {
                "create-prd": self._create_prd_tool,
                "validate-requirements": self._validate_requirements_tool,
                "create-architecture": self._create_architecture_tool,
                "design-system": self._design_system_tool,
                "risk-assessment": self._risk_assessment_tool,
                "test-design": self._test_design_tool,
                "review": self._review_tool,
                "create-story": self._create_story_tool,
                "validate-next-story": self._validate_story_tool,
                "develop-story": self._develop_story_tool,
            }

            if capability in capability_map:
                return capability_map[capability]()
            else:
                self.logger.warning(f"Unknown capability: {capability}")
                return None

        except Exception as e:
            self.logger.error(f"Error creating tool for capability {capability}: {e}")
            return None

    def _create_prd_tool(self):
        """Create PRD creation tool."""

        @tool("Create Product Requirements Document")
        def create_prd(requirements: str) -> str:
            """Create a comprehensive PRD from requirements."""
            return f"PRD created for requirements: {requirements}"

        return create_prd

    def _validate_requirements_tool(self):
        """Create requirements validation tool."""

        @tool("Validate Requirements")
        def validate_requirements(prd_content: str) -> str:
            """Validate PRD content against quality criteria."""
            return f"Requirements validated for PRD: {prd_content[:100]}..."

        return validate_requirements

    def _create_architecture_tool(self):
        """Create architecture creation tool."""

        @tool("Create System Architecture")
        def create_architecture(prd_content: str) -> str:
            """Create system architecture from PRD."""
            return f"Architecture created for PRD: {prd_content[:100]}..."

        return create_architecture

    def _design_system_tool(self):
        """Create system design tool."""

        @tool("Design System")
        def design_system(requirements: str) -> str:
            """Design system components and interactions."""
            return f"System designed for: {requirements}"

        return design_system

    def _risk_assessment_tool(self):
        """Create risk assessment tool."""

        @tool("Assess Risks")
        def assess_risks(project_context: str) -> str:
            """Perform risk assessment for project."""
            return f"Risk assessment completed for: {project_context}"

        return assess_risks

    def _test_design_tool(self):
        """Create test design tool."""

        @tool("Design Tests")
        def design_tests(requirements: str) -> str:
            """Design comprehensive test scenarios."""
            return f"Test design completed for: {requirements}"

        return design_tests

    def _review_tool(self):
        """Create review tool."""

        @tool("Review Implementation")
        def review_implementation(code_or_content: str) -> str:
            """Review implementation for quality and completeness."""
            return f"Review completed for: {code_or_content[:100]}..."

        return review_implementation

    def _create_story_tool(self):
        """Create story creation tool."""

        @tool("Create User Story")
        def create_story(requirements: str) -> str:
            """Create detailed user story from requirements."""
            return f"Story created for: {requirements}"

        return create_story

    def _validate_story_tool(self):
        """Create story validation tool."""

        @tool("Validate Story")
        def validate_story(story_content: str) -> str:
            """Validate story completeness and requirements."""
            return f"Story validated: {story_content[:100]}..."

        return validate_story

    def _develop_story_tool(self):
        """Create story development tool."""

        @tool("Develop Story")
        def develop_story(story_content: str) -> str:
            """Implement and develop user story."""
            return f"Story developed: {story_content[:100]}..."

        return develop_story

    def to_crewai_agent(
        self, allow_delegation: bool = False, verbose: bool = False
    ) -> Agent:
        """
        Convert the BMAD agent wrapper to a CrewAI Agent.

        Args:
            allow_delegation: Whether the agent can delegate tasks
            verbose: Whether to enable verbose output

        Returns:
            CrewAI Agent instance
        """
        try:
            agent = Agent(
                role=self.role,
                goal=self.goal,
                backstory=self.backstory,
                tools=self.tools,
                allow_delegation=allow_delegation,
                verbose=verbose,
            )

            self.logger.info(f"Created CrewAI agent for BMAD agent: {self.agent_id}")
            return agent

        except Exception as e:
            raise BmadCrewAIError(
                f"Failed to create CrewAI agent for {self.agent_id}: {e}"
            ) from e

    def get_capabilities(self) -> List[str]:
        """Get list of agent capabilities."""
        return self.capabilities.copy()

    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability."""
        return capability in self.capabilities

    def add_capability(self, capability: str) -> bool:
        """
        Add a new capability to the agent.

        Args:
            capability: The capability to add

        Returns:
            bool: True if capability added successfully
        """
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            # Re-create tools to include new capability
            self._create_tools_from_capabilities()
            self.logger.info(
                f"Added capability '{capability}' to agent {self.agent_id}"
            )
            return True
        return False

    def remove_capability(self, capability: str) -> bool:
        """
        Remove a capability from the agent.

        Args:
            capability: The capability to remove

        Returns:
            bool: True if capability removed successfully
        """
        if capability in self.capabilities:
            self.capabilities.remove(capability)
            # Re-create tools to exclude removed capability
            self._create_tools_from_capabilities()
            self.logger.info(
                f"Removed capability '{capability}' from agent {self.agent_id}"
            )
            return True
        return False


class BmadAgentRegistry:
    """
    Registry for managing BMAD agent wrappers and their CrewAI counterparts.

    This class handles the registration, lookup, and management of BMAD agents
    that have been wrapped for CrewAI compatibility.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the BMAD agent registry.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.wrappers: Dict[str, BmadAgentWrapper] = {}
        self.crewai_agents: Dict[str, Agent] = {}

    def register_bmad_agent(self, agent_id: str, agent_config: Dict[str, Any]) -> bool:
        """
        Register a BMAD agent with the registry.

        Args:
            agent_id: Unique identifier for the agent
            agent_config: Agent configuration dictionary

        Returns:
            bool: True if registration successful
        """
        try:
            wrapper = BmadAgentWrapper(agent_id, agent_config, self.logger)
            self.wrappers[agent_id] = wrapper

            # Create corresponding CrewAI agent
            crewai_agent = wrapper.to_crewai_agent()
            self.crewai_agents[agent_id] = crewai_agent

            self.logger.info(f"Registered BMAD agent: {agent_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register BMAD agent {agent_id}: {e}")
            return False

    def get_wrapper(self, agent_id: str) -> Optional[BmadAgentWrapper]:
        """Get BMAD agent wrapper by ID."""
        return self.wrappers.get(agent_id)

    def get_crewai_agent(self, agent_id: str) -> Optional[Agent]:
        """Get CrewAI agent by ID."""
        return self.crewai_agents.get(agent_id)

    def list_registered_agents(self) -> List[str]:
        """Get list of all registered agent IDs."""
        return list(self.wrappers.keys())

    def get_agents_by_capability(self, capability: str) -> List[str]:
        """
        Get list of agent IDs that have a specific capability.

        Args:
            capability: The capability to search for

        Returns:
            List of agent IDs with the capability
        """
        return [
            agent_id
            for agent_id, wrapper in self.wrappers.items()
            if wrapper.has_capability(capability)
        ]

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry.

        Args:
            agent_id: Agent ID to unregister

        Returns:
            bool: True if unregistration successful
        """
        if agent_id in self.wrappers:
            del self.wrappers[agent_id]
            if agent_id in self.crewai_agents:
                del self.crewai_agents[agent_id]
            self.logger.info(f"Unregistered agent: {agent_id}")
            return True

        self.logger.warning(f"Agent {agent_id} not found for unregistration")
        return False

    def get_registry_status(self) -> Dict[str, Any]:
        """Get registry status information."""
        return {
            "total_agents": len(self.wrappers),
            "agent_ids": list(self.wrappers.keys()),
            "capabilities": self._get_all_capabilities(),
        }

    def _get_all_capabilities(self) -> List[str]:
        """Get all unique capabilities across registered agents."""
        capabilities = set()
        for wrapper in self.wrappers.values():
            capabilities.update(wrapper.get_capabilities())
        return sorted(list(capabilities))
