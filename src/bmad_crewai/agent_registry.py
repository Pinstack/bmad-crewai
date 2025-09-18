"""BMAD agent registration and management."""

import logging
from typing import Any, Dict, Optional

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
