"""BMAD agent registration and management."""

import logging
from typing import Any, Dict, List, Optional

from crewai import Agent, Crew

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing BMAD agents."""

    def __init__(self):
        self.bmad_agents: Dict[str, Agent] = {}
        self.crew: Optional[Crew] = None
        self.logger = logging.getLogger(__name__)

    def register_bmad_agents(self) -> bool:
        """Register all BMAD agents with CrewAI.

        Returns:
            bool: True if registration successful
        """
        # Define agent configurations based on BMAD methodology
        agent_configs = {
            "scrum-master": {
                "name": "Scrum Master",
                "role": "Technical Scrum Master & Process Steward",
                "goal": "Ensure agile process adherence and create "
                "actionable development tasks",
                "backstory": "Expert in BMAD methodology, focuses on "
                "story creation and process guidance",
            },
            "product-owner": {
                "name": "Product Owner",
                "role": "Technical Product Owner & Process Steward",
                "goal": "Validate artifacts cohesion and " "coach significant changes",
                "backstory": "Guardian of quality and completeness "
                "in project artifacts",
            },
            "product-manager": {
                "name": "Product Manager",
                "role": "Investigative Product Strategist & Market-Savvy PM",
                "goal": "Creating PRDs and product documentation using templates",
                "backstory": "Specialized in document creation and product research",
            },
            "architect": {
                "name": "Architect",
                "role": "Holistic System Architect & Full-Stack Technical Leader",
                "goal": "Complete systems architecture and " "cross-stack optimization",
                "backstory": "Master of holistic application design and "
                "technology selection",
            },
            "dev-agent": {
                "name": "Full Stack Developer",
                "role": "Expert Senior Software Engineer & Implementation Specialist",
                "goal": "Execute stories with precision and " "comprehensive testing",
                "backstory": "Implements requirements with detailed task execution",
            },
            "qa-agent": {
                "name": "Test Architect & Quality Advisor",
                "role": "Test Architect with Quality Advisory Authority",
                "goal": "Provide thorough quality assessment and "
                "actionable recommendations",
                "backstory": "Comprehensive quality analysis through "
                "test architecture and risk assessment",
            },
        }

        # Register each agent
        for agent_id, config in agent_configs.items():
            try:
                agent = Agent(
                    role=config["role"],
                    goal=config["goal"],
                    backstory=config["backstory"],
                    allow_delegation=False,  # BMAD agents work independently
                    verbose=False,  # Reduce verbosity for testing
                )

                self.bmad_agents[agent_id] = agent
                self.logger.info(
                    f"Registered BMAD agent: {config['name']} ({agent_id})"
                )

            except Exception as e:
                self.logger.error(f"Failed to register agent {agent_id}: {e}")
                return False

        # Create Crew with agents (initialize properly)
        try:
            if self.bmad_agents:
                self.crew = Crew(agents=list(self.bmad_agents.values()), verbose=False)
                self.logger.info("CrewAI crew initialized with BMAD agents")
            else:
                self.logger.warning("No agents registered, Crew not initialized")
                return False
        except Exception as e:
            self.logger.error(f"Failed to initialize Crew: {e}")
            # Continue without crew for now - agents are still registered
            self.crew = None

        self.logger.info(f"Successfully registered {len(self.bmad_agents)} BMAD agents")
        return True

    def get_bmad_agent(self, agent_id: str) -> Optional[Agent]:
        """Get a registered BMAD agent by ID.

        Args:
            agent_id: Agent identifier (e.g., 'scrum-master', 'dev-agent')

        Returns:
            Agent object or None if not found
        """
        return self.bmad_agents.get(agent_id)

    def list_bmad_agents(self) -> Dict[str, Dict[str, Any]]:
        """List all registered BMAD agents.

        Returns:
            Dict of agent information
        """
        return {
            agent_id: {"name": agent.role, "goal": agent.goal, "registered": True}
            for agent_id, agent in self.bmad_agents.items()
        }

    def register_product_manager_agent(self) -> bool:
        """Register Product Manager agent with CrewAI.

        Returns:
            bool: True if registration successful
        """
        return self._register_single_agent("product-manager")

    def register_system_architect_agent(self) -> bool:
        """Register System Architect agent with CrewAI.

        Returns:
            bool: True if registration successful
        """
        return self._register_single_agent("architect")

    def register_qa_agent(self) -> bool:
        """Register QA agent with CrewAI.

        Returns:
            bool: True if registration successful
        """
        return self._register_single_agent("qa-agent")

    def register_developer_agent(self) -> bool:
        """Register Developer agent with CrewAI.

        Returns:
            bool: True if registration successful
        """
        return self._register_single_agent("dev-agent")

    def register_product_owner_agent(self) -> bool:
        """Register Product Owner agent with CrewAI.

        Returns:
            bool: True if registration successful
        """
        return self._register_single_agent("product-owner")

    def register_scrum_master_agent(self) -> bool:
        """Register Scrum Master agent with CrewAI.

        Returns:
            bool: True if registration successful
        """
        return self._register_single_agent("scrum-master")

    def _register_single_agent(self, agent_id: str) -> bool:
        """Register a single BMAD agent by ID.

        Args:
            agent_id: The agent identifier to register

        Returns:
            bool: True if registration successful
        """
        try:
            # Get agent configuration
            agent_configs = self._get_agent_configs()
            if agent_id not in agent_configs:
                self.logger.error(f"Unknown agent ID: {agent_id}")
                return False

            config = agent_configs[agent_id]

            # Create and register agent
            agent = Agent(
                role=config["role"],
                goal=config["goal"],
                backstory=config["backstory"],
                allow_delegation=False,
                verbose=False,
            )

            self.bmad_agents[agent_id] = agent
            self.logger.info(f"Registered BMAD agent: {config['name']} ({agent_id})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    def validate_agent_registration(self, agent_id: str) -> Dict[str, Any]:
        """Validate that an agent is properly registered and functional.

        Args:
            agent_id: Agent identifier to validate

        Returns:
            Dict with validation results
        """
        results = {
            "agent_id": agent_id,
            "registered": False,
            "has_required_attributes": False,
            "crewai_compatible": False,
            "validation_errors": [],
        }

        try:
            agent = self.bmad_agents.get(agent_id)
            if not agent:
                results["validation_errors"].append(f"Agent {agent_id} not found")
                return results

            results["registered"] = True

            # Check required attributes
            required_attrs = ["role", "goal", "backstory"]
            missing_attrs = []
            for attr in required_attrs:
                if not hasattr(agent, attr):
                    missing_attrs.append(attr)

            if missing_attrs:
                results["validation_errors"].extend(
                    [f"Missing attribute: {attr}" for attr in missing_attrs]
                )
            else:
                results["has_required_attributes"] = True

            # Check CrewAI compatibility
            if hasattr(agent, "_executor") or hasattr(agent, "llm"):
                results["crewai_compatible"] = True
            else:
                results["validation_errors"].append(
                    "Agent may not be CrewAI compatible"
                )

        except Exception as e:
            results["validation_errors"].append(f"Validation error: {e}")

        return results

    def get_registration_status(self) -> Dict[str, Any]:
        """Get comprehensive registration status for all BMAD agents.

        Returns:
            Dict with registration status details
        """
        status = {
            "total_agents": len(self.bmad_agents),
            "expected_agents": 6,
            "registration_complete": len(self.bmad_agents) == 6,
            "crew_initialized": self.crew is not None,
            "agent_status": {},
            "errors": [],
        }

        # Check each expected agent
        expected_agents = [
            "scrum-master",
            "product-owner",
            "product-manager",
            "architect",
            "dev-agent",
            "qa-agent",
        ]

        for agent_id in expected_agents:
            if agent_id in self.bmad_agents:
                validation = self.validate_agent_registration(agent_id)
                status["agent_status"][agent_id] = {
                    "registered": True,
                    "valid": len(validation["validation_errors"]) == 0,
                    "errors": validation["validation_errors"],
                }
            else:
                status["agent_status"][agent_id] = {
                    "registered": False,
                    "valid": False,
                    "errors": ["Agent not registered"],
                }
                status["errors"].append(f"Missing agent: {agent_id}")

        return status

    def _get_agent_configs(self) -> Dict[str, Dict[str, str]]:
        """Get the configuration for all BMAD agents.

        Returns:
            Dict of agent configurations
        """
        return {
            "scrum-master": {
                "name": "Scrum Master",
                "role": "Technical Scrum Master & Process Steward",
                "goal": "Ensure agile process adherence and create actionable development tasks",
                "backstory": "Expert in BMAD methodology, focuses on story creation and process guidance",
            },
            "product-owner": {
                "name": "Product Owner",
                "role": "Technical Product Owner & Process Steward",
                "goal": "Validate artifacts cohesion and coach significant changes",
                "backstory": "Guardian of quality and completeness in project artifacts",
            },
            "product-manager": {
                "name": "Product Manager",
                "role": "Investigative Product Strategist & Market-Savvy PM",
                "goal": "Creating PRDs and product documentation using templates",
                "backstory": "Specialized in document creation and product research",
            },
            "architect": {
                "name": "Architect",
                "role": "Holistic System Architect & Full-Stack Technical Leader",
                "goal": "Complete systems architecture and cross-stack optimization",
                "backstory": "Master of holistic application design and technology selection",
            },
            "dev-agent": {
                "name": "Full Stack Developer",
                "role": "Expert Senior Software Engineer & Implementation Specialist",
                "goal": "Execute stories with precision and comprehensive testing",
                "backstory": "Implements requirements with detailed task execution",
            },
            "qa-agent": {
                "name": "Test Architect & Quality Advisor",
                "role": "Test Architect with Quality Advisory Authority",
                "goal": "Provide thorough quality assessment and actionable recommendations",
                "backstory": "Comprehensive quality analysis through test architecture and risk assessment",
            },
        }

    def test_agent_coordination(self) -> Dict[str, Any]:
        """Test agent coordination and crew functionality.

        Returns:
            Dict with coordination test results
        """
        results = {
            "agent_registration": len(self.bmad_agents) > 0,
            "crew_initialization": self.crew is not None,
            "coordination_test": False,
        }

        # Test basic coordination
        if self.crew and self.bmad_agents:
            try:
                # Simple coordination test - check if we can access agent methods
                test_agent = list(self.bmad_agents.values())[0]
                if hasattr(test_agent, "role") and hasattr(test_agent, "goal"):
                    results["coordination_test"] = True
                    self.logger.info("Agent coordination test passed")
                else:
                    self.logger.warning(
                        "Agent coordination test failed - missing attributes"
                    )
            except Exception as e:
                self.logger.error(f"Agent coordination test failed: {e}")

        return results

    def track_agent_handoff(self, workflow_id: str, from_agent: str, to_agent: str,
                          handoff_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Track agent handoffs for workflow state management.

        Args:
            workflow_id: Workflow identifier
            from_agent: Agent handing off
            to_agent: Agent receiving handoff
            handoff_data: Optional data associated with handoff

        Returns:
            bool: True if tracking successful, False otherwise
        """
        try:
            # This method serves as a bridge to WorkflowStateManager
            # In a full implementation, this would delegate to the state manager
            # For now, we'll log the handoff for future integration

            handoff_record = {
                "workflow_id": workflow_id,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "timestamp": logger.info(f"Agent handoff tracked: {from_agent} → {to_agent} in workflow {workflow_id}"),
                "data": handoff_data or {}
            }

            # Store handoff in agent metadata for now
            # In full implementation, this would be handled by WorkflowStateManager
            if not hasattr(self, '_agent_handoffs'):
                self._agent_handoffs = []

            self._agent_handoffs.append(handoff_record)

            self.logger.info(
                f"Agent handoff tracked: {from_agent} → {to_agent} in workflow {workflow_id}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to track agent handoff: {e}")
            return False

    def get_agent_handoffs(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get agent handoff records, optionally filtered by workflow.

        Args:
            workflow_id: Optional workflow ID to filter by

        Returns:
            List[Dict[str, Any]]: List of handoff records
        """
        try:
            handoffs = getattr(self, '_agent_handoffs', [])

            if workflow_id:
                handoffs = [h for h in handoffs if h.get("workflow_id") == workflow_id]

            return handoffs

        except Exception as e:
            self.logger.error(f"Failed to get agent handoffs: {e}")
            return []

    def get_agent_dependencies(self, workflow_id: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get agent dependency mapping from handoffs.

        Args:
            workflow_id: Optional workflow ID to filter by

        Returns:
            Dict[str, List[str]]: Agent dependency mapping
        """
        try:
            dependencies = {}
            handoffs = self.get_agent_handoffs(workflow_id)

            for handoff in handoffs:
                from_agent = handoff.get("from_agent")
                to_agent = handoff.get("to_agent")

                if from_agent and to_agent:
                    if from_agent not in dependencies:
                        dependencies[from_agent] = []

                    if to_agent not in dependencies[from_agent]:
                        dependencies[from_agent].append(to_agent)

            return dependencies

        except Exception as e:
            self.logger.error(f"Failed to get agent dependencies: {e}")
            return {}

    def validate_agent_handoff(self, from_agent: str, to_agent: str,
                             workflow_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate an agent handoff before execution.

        Args:
            from_agent: Agent handing off
            to_agent: Agent receiving handoff
            workflow_context: Optional workflow context information

        Returns:
            Dict[str, Any]: Validation result with status and details
        """
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }

        try:
            # Check if agents exist
            if from_agent not in self.bmad_agents:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Source agent '{from_agent}' not registered")

            if to_agent not in self.bmad_agents:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Target agent '{to_agent}' not registered")

            if not validation_result["is_valid"]:
                return validation_result

            # Check agent capabilities for handoff
            from_agent_obj = self.bmad_agents[from_agent]
            to_agent_obj = self.bmad_agents[to_agent]

            # Validate agent roles are compatible for handoff
            compatible_handoffs = {
                "scrum-master": ["product-owner", "dev-agent", "qa-agent"],
                "product-owner": ["product-manager", "architect", "scrum-master"],
                "product-manager": ["architect", "product-owner"],
                "architect": ["dev-agent", "qa-agent", "product-manager"],
                "dev-agent": ["qa-agent", "architect", "scrum-master"],
                "qa-agent": ["dev-agent", "architect", "product-owner"]
            }

            if from_agent in compatible_handoffs:
                if to_agent not in compatible_handoffs[from_agent]:
                    validation_result["warnings"].append(
                        f"Unusual handoff: {from_agent} → {to_agent} (not in standard workflow)"
                    )

            # Check for circular dependencies in recent handoffs
            recent_handoffs = self.get_agent_handoffs()[-10:]  # Last 10 handoffs

            # Simple circular dependency check
            for handoff in recent_handoffs:
                if (handoff.get("from_agent") == to_agent and
                    handoff.get("to_agent") == from_agent):
                    validation_result["warnings"].append(
                        f"Potential circular dependency detected: {from_agent} ↔ {to_agent}"
                    )
                    break

            # Check workflow context if provided
            if workflow_context:
                current_step = workflow_context.get("current_step", "")
                workflow_status = workflow_context.get("status", "")

                if workflow_status not in ["running", "initialized"]:
                    validation_result["warnings"].append(
                        f"Workflow status is {workflow_status}, handoff may not be appropriate"
                    )

        except Exception as e:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")

        return validation_result

    def get_agent_handoff_history(self, agent_id: str, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get handoff history for a specific agent.

        Args:
            agent_id: Agent identifier
            workflow_id: Optional workflow ID to filter by

        Returns:
            List[Dict[str, Any]]: Handoff history for the agent
        """
        try:
            all_handoffs = self.get_agent_handoffs(workflow_id)

            # Filter handoffs involving this agent
            agent_handoffs = []
            for handoff in all_handoffs:
                if handoff.get("from_agent") == agent_id or handoff.get("to_agent") == agent_id:
                    agent_handoffs.append(handoff)

            return agent_handoffs

        except Exception as e:
            self.logger.error(f"Failed to get agent handoff history: {e}")
            return []
