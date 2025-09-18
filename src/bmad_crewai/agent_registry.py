"""BMAD agent registration and management."""

import logging
from typing import Any, Dict, List, Optional

from crewai import Agent, Crew

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing BMAD agents."""

    def __init__(self, model_config: Optional[Dict[str, Any]] = None):
        self.bmad_agents: Dict[str, Agent] = {}
        self.crew: Optional[Crew] = None
        self.logger = logging.getLogger(__name__)
        self.model_config = model_config or {}

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
                # Configure LLM based on available model settings
                agent_kwargs = {
                    "role": config["role"],
                    "goal": config["goal"],
                    "backstory": config["backstory"],
                    "allow_delegation": False,  # BMAD agents work independently
                    "verbose": False,  # Reduce verbosity for testing
                }

                # Add LLM configuration if available
                if self.model_config:
                    from crewai import LLM

                    llm = self._create_llm_config()
                    if llm:
                        agent_kwargs["llm"] = llm

                agent = Agent(**agent_kwargs)

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

    def _create_llm_config(self) -> Optional["LLM"]:
        """
        Create LLM configuration with fallback support.

        Returns:
            LLM instance or None if no valid configuration found
        """
        try:
            from crewai import LLM

            # Try OpenRouter first (primary)
            if self.model_config.get("provider") == "openrouter":
                api_key = self.model_config.get("api_key")
                model = self.model_config.get("model")
                base_url = self.model_config.get("base_url")

                if api_key and model and base_url:
                    try:
                        return LLM(
                            model=model,
                            api_key=api_key,
                            base_url=base_url,
                            temperature=0.7,
                            max_tokens=4000,
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to configure OpenRouter LLM: {e}")

            # Fallback to OpenAI if available
            openai_key = self.model_config.get("openai_api_key")
            if openai_key:
                try:
                    return LLM(
                        model="gpt-4",
                        api_key=openai_key,
                        temperature=0.7,
                        max_tokens=4000,
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to configure OpenAI fallback LLM: {e}")

            # No valid LLM configuration available
            self.logger.info("No LLM configuration available, using CrewAI defaults")
            return None

        except ImportError:
            self.logger.warning("CrewAI LLM import failed, using defaults")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error configuring LLM: {e}")
            return None

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

    def track_agent_handoff(
        self,
        workflow_id: str,
        from_agent: str,
        to_agent: str,
        handoff_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
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
                "timestamp": logger.info(
                    f"Agent handoff tracked: {from_agent} → {to_agent} in workflow {workflow_id}"
                ),
                "data": handoff_data or {},
            }

            # Store handoff in agent metadata for now
            # In full implementation, this would be handled by WorkflowStateManager
            if not hasattr(self, "_agent_handoffs"):
                self._agent_handoffs = []

            self._agent_handoffs.append(handoff_record)

            self.logger.info(
                f"Agent handoff tracked: {from_agent} → {to_agent} in workflow {workflow_id}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to track agent handoff: {e}")
            return False

    def get_agent_handoffs(
        self, workflow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get agent handoff records, optionally filtered by workflow.

        Args:
            workflow_id: Optional workflow ID to filter by

        Returns:
            List[Dict[str, Any]]: List of handoff records
        """
        try:
            handoffs = getattr(self, "_agent_handoffs", [])

            if workflow_id:
                handoffs = [h for h in handoffs if h.get("workflow_id") == workflow_id]

            return handoffs

        except Exception as e:
            self.logger.error(f"Failed to get agent handoffs: {e}")
            return []

    def get_agent_dependencies(
        self, workflow_id: Optional[str] = None
    ) -> Dict[str, List[str]]:
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

    def validate_agent_handoff(
        self,
        from_agent: str,
        to_agent: str,
        workflow_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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
            "recommendations": [],
        }

        try:
            # Check if agents exist
            if from_agent not in self.bmad_agents:
                validation_result["is_valid"] = False
                validation_result["errors"].append(
                    f"Source agent '{from_agent}' not registered"
                )

            if to_agent not in self.bmad_agents:
                validation_result["is_valid"] = False
                validation_result["errors"].append(
                    f"Target agent '{to_agent}' not registered"
                )

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
                "qa-agent": ["dev-agent", "architect", "product-owner"],
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
                if (
                    handoff.get("from_agent") == to_agent
                    and handoff.get("to_agent") == from_agent
                ):
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

    def get_agent_handoff_history(
        self, agent_id: str, workflow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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
                if (
                    handoff.get("from_agent") == agent_id
                    or handoff.get("to_agent") == agent_id
                ):
                    agent_handoffs.append(handoff)

            return agent_handoffs

        except Exception as e:
            self.logger.error(f"Failed to get agent handoff history: {e}")
            return []

    def get_optimal_agent(
        self,
        task_requirements: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get the optimal agent for a task based on requirements, context, and performance.

        Args:
            task_requirements: Task requirements and capabilities needed
            context: Optional workflow context
            workflow_id: Optional workflow ID for context

        Returns:
            Optional[str]: Best agent ID or None if no suitable agent found
        """
        try:
            # Get all available agents
            available_agents = self._get_available_agents()

            if not available_agents:
                self.logger.warning("No agents available for task assignment")
                return None

            # Score each agent based on requirements and context
            agent_scores = {}
            for agent_id in available_agents:
                score = self._calculate_agent_score(
                    agent_id, task_requirements, context, workflow_id
                )
                agent_scores[agent_id] = score

            # Return agent with highest score
            if agent_scores:
                best_agent = max(agent_scores.items(), key=lambda x: x[1])
                self.logger.info(
                    f"Selected optimal agent {best_agent[0]} with score {best_agent[1]}"
                )
                return best_agent[0]

        except Exception as e:
            self.logger.error(f"Failed to get optimal agent: {e}")

        return None

    def _get_available_agents(self) -> List[str]:
        """Get list of currently available agents."""
        # For now, return all registered agents
        # In future, this could check agent availability, load, etc.
        return list(self.bmad_agents.keys())

    def _calculate_agent_score(
        self,
        agent_id: str,
        task_requirements: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
    ) -> float:
        """
        Calculate suitability score for an agent based on task requirements.

        Args:
            agent_id: Agent identifier
            task_requirements: Task requirements
            context: Optional workflow context
            workflow_id: Optional workflow ID

        Returns:
            float: Suitability score (0.0 to 1.0)
        """
        score = 0.0
        total_weight = 0.0

        try:
            # Capability matching (weight: 0.4)
            capability_score = self._score_capability_match(agent_id, task_requirements)
            score += capability_score * 0.4
            total_weight += 0.4

            # Performance history (weight: 0.3)
            performance_score = self._score_performance_history(
                agent_id, task_requirements, workflow_id
            )
            score += performance_score * 0.3
            total_weight += 0.3

            # Load balancing (weight: 0.2)
            load_score = self._score_load_balance(agent_id, workflow_id)
            score += load_score * 0.2
            total_weight += 0.2

            # Context compatibility (weight: 0.1)
            context_score = self._score_context_compatibility(agent_id, context)
            score += context_score * 0.1
            total_weight += 0.1

            # Normalize score
            final_score = score / total_weight if total_weight > 0 else 0.0

            return max(0.0, min(1.0, final_score))

        except Exception as e:
            self.logger.warning(f"Failed to calculate agent score for {agent_id}: {e}")
            return 0.0

    def _score_capability_match(
        self, agent_id: str, task_requirements: Dict[str, Any]
    ) -> float:
        """Score agent based on capability match with task requirements."""
        agent_capabilities = self._get_agent_capabilities(agent_id)
        task_capabilities = task_requirements.get("capabilities", [])

        if not task_capabilities:
            return 1.0  # No specific requirements, full score

        if not agent_capabilities:
            return 0.0  # No capabilities defined

        # Calculate match ratio
        matches = 0
        for req_cap in task_capabilities:
            if req_cap in agent_capabilities:
                matches += 1

        return matches / len(task_capabilities) if task_capabilities else 1.0

    def _get_agent_capabilities(self, agent_id: str) -> List[str]:
        """Get capabilities for an agent."""
        # Define agent capabilities based on BMAD methodology
        agent_capabilities = {
            "scrum-master": ["coordination", "process", "facilitation", "agile"],
            "product-owner": ["requirements", "validation", "stakeholder", "backlog"],
            "product-manager": ["strategy", "market", "roadmap", "stakeholder"],
            "architect": ["design", "architecture", "technical", "patterns"],
            "dev-agent": ["implementation", "coding", "debugging", "testing"],
            "qa-agent": ["testing", "quality", "validation", "automation"],
        }

        return agent_capabilities.get(agent_id, [])

    def _score_performance_history(
        self,
        agent_id: str,
        task_requirements: Dict[str, Any],
        workflow_id: Optional[str] = None,
    ) -> float:
        """Score agent based on historical performance."""
        # For now, use handoff history as performance indicator
        # In future, this could use actual performance metrics

        handoffs = self.get_agent_handoff_history(agent_id, workflow_id)
        if not handoffs:
            return 0.5  # Neutral score for no history

        # Calculate success rate from handoffs
        successful_handoffs = sum(1 for h in handoffs if not h.get("error"))
        success_rate = successful_handoffs / len(handoffs) if handoffs else 0.5

        return success_rate

    def _score_load_balance(
        self, agent_id: str, workflow_id: Optional[str] = None
    ) -> float:
        """Score agent based on current load balancing."""
        # Simple load balancing based on recent handoffs
        recent_handoffs = self.get_agent_handoffs(workflow_id)

        if not recent_handoffs:
            return 1.0  # No recent activity, fully available

        # Count recent assignments for this agent
        agent_assignments = sum(
            1
            for h in recent_handoffs[-20:]  # Last 20 handoffs
            if h.get("to_agent") == agent_id
        )

        # Calculate load score (lower assignments = higher score)
        max_expected_load = 5  # Arbitrary threshold
        load_factor = min(agent_assignments / max_expected_load, 1.0)

        # Return inverse (higher availability = higher score)
        return 1.0 - load_factor

    def _score_context_compatibility(
        self, agent_id: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Score agent based on workflow context compatibility."""
        if not context:
            return 1.0  # No context, full compatibility

        # Check workflow phase compatibility
        workflow_phase = context.get("phase", "")
        agent_workflow_phases = {
            "scrum-master": ["planning", "review", "retrospective"],
            "product-owner": ["requirements", "validation", "acceptance"],
            "product-manager": ["strategy", "roadmap", "analysis"],
            "architect": ["design", "architecture", "technical"],
            "dev-agent": ["implementation", "development", "coding"],
            "qa-agent": ["testing", "validation", "quality"],
        }

        compatible_phases = agent_workflow_phases.get(agent_id, [])
        if workflow_phase and workflow_phase in compatible_phases:
            return 1.0

        # Partial compatibility if phase is related
        if workflow_phase:
            return 0.5

        return 1.0  # Default compatibility

    def get_agent_performance_metrics(
        self, agent_id: str, workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics for an agent.

        Args:
            agent_id: Agent identifier
            workflow_id: Optional workflow ID to filter metrics

        Returns:
            Dict[str, Any]: Performance metrics
        """
        try:
            handoffs = self.get_agent_handoff_history(agent_id, workflow_id)

            metrics = {
                "total_handoffs": len(handoffs),
                "successful_handoffs": sum(1 for h in handoffs if not h.get("error")),
                "average_handoff_time": 0.0,  # Placeholder for future implementation
                "error_rate": 0.0,
                "availability_score": self._score_load_balance(agent_id, workflow_id),
            }

            if metrics["total_handoffs"] > 0:
                metrics["error_rate"] = 1.0 - (
                    metrics["successful_handoffs"] / metrics["total_handoffs"]
                )
                metrics["success_rate"] = (
                    metrics["successful_handoffs"] / metrics["total_handoffs"]
                )

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to get performance metrics for {agent_id}: {e}")
            return {
                "total_handoffs": 0,
                "successful_handoffs": 0,
                "error_rate": 0.0,
                "availability_score": 0.5,
            }

    def optimize_agent_assignment(
        self,
        task_requirements: Dict[str, Any],
        available_agents: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize agent assignment for a task with detailed analysis.

        Args:
            task_requirements: Task requirements
            available_agents: Optional list of available agents
            context: Optional workflow context

        Returns:
            Dict[str, Any]: Optimization result with recommendations
        """
        try:
            if available_agents is None:
                available_agents = self._get_available_agents()

            optimization_result = {
                "recommended_agent": None,
                "confidence_score": 0.0,
                "alternatives": [],
                "reasoning": {},
                "optimization_factors": {},
            }

            # Calculate scores for all available agents
            agent_scores = {}
            for agent_id in available_agents:
                score = self._calculate_agent_score(
                    agent_id, task_requirements, context
                )
                agent_scores[agent_id] = score

            if not agent_scores:
                return optimization_result

            # Sort by score (descending)
            sorted_agents = sorted(
                agent_scores.items(), key=lambda x: x[1], reverse=True
            )

            # Set recommended agent
            best_agent, best_score = sorted_agents[0]
            optimization_result["recommended_agent"] = best_agent
            optimization_result["confidence_score"] = best_score

            # Add alternatives (top 3)
            optimization_result["alternatives"] = [
                {"agent": agent, "score": score}
                for agent, score in sorted_agents[1:4]  # Next 3 best
            ]

            # Add reasoning
            optimization_result["reasoning"] = {
                "capability_match": self._score_capability_match(
                    best_agent, task_requirements
                ),
                "performance_history": self._score_performance_history(
                    best_agent, task_requirements
                ),
                "load_balance": self._score_load_balance(best_agent),
                "context_compatibility": self._score_context_compatibility(
                    best_agent, context
                ),
            }

            # Add optimization factors
            optimization_result["optimization_factors"] = {
                "capability_weight": 0.4,
                "performance_weight": 0.3,
                "load_weight": 0.2,
                "context_weight": 0.1,
                "total_agents_considered": len(available_agents),
            }

            return optimization_result

        except Exception as e:
            self.logger.error(f"Failed to optimize agent assignment: {e}")
            return {
                "recommended_agent": None,
                "confidence_score": 0.0,
                "alternatives": [],
                "reasoning": {"error": str(e)},
                "optimization_factors": {},
            }

    # Performance tracking extension methods for monitoring and analytics

    def track_performance(self, agent_id: str, task_metrics: Dict[str, Any]) -> bool:
        """
        Track agent performance metrics for monitoring and analytics.

        Args:
            agent_id: Agent identifier
            task_metrics: Performance metrics from task execution

        Returns:
            bool: True if tracking successful, False otherwise
        """
        try:
            if agent_id not in self.bmad_agents:
                self.logger.warning(f"Agent {agent_id} not found in registry")
                return False

            # Initialize performance tracking if not exists
            if not hasattr(self, "_agent_performance"):
                self._agent_performance = {}
            if agent_id not in self._agent_performance:
                self._agent_performance[agent_id] = {
                    "total_tasks": 0,
                    "successful_tasks": 0,
                    "failed_tasks": 0,
                    "response_times": [],
                    "error_types": {},
                    "last_activity": None,
                    "utilization_rate": 0.0,
                    "success_rate_history": [],
                    "response_time_history": [],
                }

            perf_data = self._agent_performance[agent_id]

            # Update basic metrics
            perf_data["total_tasks"] += 1
            perf_data["last_activity"] = task_metrics.get("timestamp")

            # Track success/failure
            if task_metrics.get("success", False):
                perf_data["successful_tasks"] += 1
            else:
                perf_data["failed_tasks"] += 1
                error_type = task_metrics.get("error_type", "unknown")
                perf_data["error_types"][error_type] = (
                    perf_data["error_types"].get(error_type, 0) + 1
                )

            # Track response time
            response_time = task_metrics.get("response_time")
            if response_time is not None:
                perf_data["response_times"].append(response_time)
                perf_data["response_time_history"].append(
                    {
                        "timestamp": task_metrics.get("timestamp"),
                        "duration": response_time,
                        "task_type": task_metrics.get("task_type", "unknown"),
                    }
                )

            # Calculate success rate
            if perf_data["total_tasks"] > 0:
                current_success_rate = (
                    perf_data["successful_tasks"] / perf_data["total_tasks"]
                )
                perf_data["success_rate_history"].append(
                    {
                        "timestamp": task_metrics.get("timestamp"),
                        "rate": current_success_rate,
                    }
                )

            # Update utilization rate (simple moving average)
            recent_tasks = min(10, len(perf_data["success_rate_history"]))
            if recent_tasks > 0:
                recent_success_rate = (
                    sum(
                        entry["rate"]
                        for entry in perf_data["success_rate_history"][-recent_tasks:]
                    )
                    / recent_tasks
                )
                perf_data["utilization_rate"] = recent_success_rate

            self.logger.debug(
                f"Tracked performance for agent {agent_id}: success={task_metrics.get('success', False)}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to track performance for agent {agent_id}: {e}")
            return False

    def get_agent_performance_history(self, agent_id: str) -> Dict[str, Any]:
        """
        Get comprehensive performance history for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary with performance history and trends
        """
        try:
            if (
                not hasattr(self, "_agent_performance")
                or agent_id not in self._agent_performance
            ):
                return {"error": f"No performance data available for agent {agent_id}"}

            perf_data = self._agent_performance[agent_id]

            # Calculate response time statistics
            response_times = perf_data.get("response_times", [])
            response_stats = {}
            if response_times:
                response_stats = {
                    "average_response_time": sum(response_times) / len(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "median_response_time": sorted(response_times)[
                        len(response_times) // 2
                    ],
                    "response_time_variance": (
                        sum(
                            (x - response_stats.get("average_response_time", 0)) ** 2
                            for x in response_times
                        )
                        / len(response_times)
                        if response_times
                        else 0
                    ),
                }

            # Calculate success rate trends
            success_history = perf_data.get("success_rate_history", [])
            trend_direction = "stable"
            if len(success_history) >= 2:
                recent_rates = [entry["rate"] for entry in success_history[-5:]]
                if len(recent_rates) >= 2:
                    trend = recent_rates[-1] - recent_rates[0]
                    if trend > 0.05:
                        trend_direction = "improving"
                    elif trend < -0.05:
                        trend_direction = "degrading"

            # Calculate error distribution
            error_distribution = {}
            total_errors = sum(perf_data.get("error_types", {}).values())
            if total_errors > 0:
                for error_type, count in perf_data["error_types"].items():
                    error_distribution[error_type] = {
                        "count": count,
                        "percentage": (count / total_errors) * 100,
                    }

            return {
                "agent_id": agent_id,
                "total_tasks": perf_data["total_tasks"],
                "successful_tasks": perf_data["successful_tasks"],
                "failed_tasks": perf_data["failed_tasks"],
                "success_rate": (
                    perf_data["successful_tasks"] / perf_data["total_tasks"]
                    if perf_data["total_tasks"] > 0
                    else 0
                ),
                "utilization_rate": perf_data["utilization_rate"],
                "response_time_stats": response_stats,
                "trend_direction": trend_direction,
                "error_distribution": error_distribution,
                "last_activity": perf_data["last_activity"],
                "performance_score": self._calculate_performance_score(perf_data),
            }

        except Exception as e:
            self.logger.error(
                f"Failed to get performance history for agent {agent_id}: {e}"
            )
            return {"error": str(e)}

    def _calculate_performance_score(self, perf_data: Dict[str, Any]) -> float:
        """Calculate overall performance score for an agent (0-100)."""
        if perf_data["total_tasks"] == 0:
            return 50.0  # Neutral score for new agents

        success_rate = perf_data["successful_tasks"] / perf_data["total_tasks"]
        utilization_rate = perf_data["utilization_rate"]

        # Weight factors: success (50%), utilization (30%), consistency (20%)
        score = (
            success_rate * 50
            + utilization_rate * 30
            + (
                1
                - len(perf_data.get("error_types", {}))
                / max(perf_data["total_tasks"], 1)
            )
            * 20
        )

        return min(100.0, max(0.0, score))

    def get_agent_performance_trends(
        self, agent_id: str, window_size: int = 10
    ) -> Dict[str, Any]:
        """Get performance trends over recent tasks."""
        try:
            if (
                not hasattr(self, "_agent_performance")
                or agent_id not in self._agent_performance
            ):
                return {"error": f"No performance data available for agent {agent_id}"}

            perf_data = self._agent_performance[agent_id]
            success_history = perf_data.get("success_rate_history", [])
            response_history = perf_data.get("response_time_history", [])

            if len(success_history) < 2:
                return {"insufficient_data": True}

            # Analyze success rate trend
            recent_success = (
                success_history[-window_size:]
                if len(success_history) >= window_size
                else success_history
            )
            success_trend = "stable"
            if len(recent_success) >= 2:
                early_avg = sum(
                    entry["rate"]
                    for entry in recent_success[: len(recent_success) // 2]
                ) / (len(recent_success) // 2)
                late_avg = sum(
                    entry["rate"]
                    for entry in recent_success[len(recent_success) // 2 :]
                ) / (len(recent_success) // 2)
                if late_avg > early_avg + 0.05:
                    success_trend = "improving"
                elif late_avg < early_avg - 0.05:
                    success_trend = "degrading"

            # Analyze response time trend
            response_trend = "stable"
            if len(response_history) >= window_size:
                recent_responses = response_history[-window_size:]
                early_avg = sum(
                    entry["duration"]
                    for entry in recent_responses[: len(recent_responses) // 2]
                ) / (len(recent_responses) // 2)
                late_avg = sum(
                    entry["duration"]
                    for entry in recent_responses[len(recent_responses) // 2 :]
                ) / (len(recent_responses) // 2)
                if late_avg < early_avg * 0.9:
                    response_trend = "improving"
                elif late_avg > early_avg * 1.1:
                    response_trend = "degrading"

            return {
                "success_rate_trend": success_trend,
                "response_time_trend": response_trend,
                "analysis_window": len(recent_success),
                "recommendations": self._generate_performance_recommendations(
                    success_trend, response_trend
                ),
            }

        except Exception as e:
            self.logger.error(
                f"Failed to get performance trends for agent {agent_id}: {e}"
            )
            return {"error": str(e)}

    def _generate_performance_recommendations(
        self, success_trend: str, response_trend: str
    ) -> List[str]:
        """Generate recommendations based on performance trends."""
        recommendations = []

        if success_trend == "degrading":
            recommendations.append(
                "Review recent task failures and implement error recovery improvements"
            )
        elif success_trend == "improving":
            recommendations.append(
                "Continue current successful patterns and document best practices"
            )

        if response_trend == "degrading":
            recommendations.append(
                "Investigate causes of increasing response times and optimize performance"
            )
        elif response_trend == "improving":
            recommendations.append("Maintain current optimization strategies")

        if success_trend == "stable" and response_trend == "stable":
            recommendations.append(
                "Performance is stable - consider monitoring for optimization opportunities"
            )

        return recommendations
