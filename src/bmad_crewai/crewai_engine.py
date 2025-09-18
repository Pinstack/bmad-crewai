"""
CrewAI Orchestration Engine for BMAD Framework

This module provides the core CrewAI orchestration functionality for the BMAD framework.
It manages CrewAI crews, workflows, and agent coordination.
"""

import logging
from typing import Any, Dict, List, Optional

from crewai import Agent, Crew, Process, Task

from .exceptions import BmadCrewAIError


class CrewAIOrchestrationEngine:
    """
    Core orchestration class managing CrewAI crews and workflows for BMAD framework.

    This engine handles:
    - CrewAI crew initialization and management
    - Workflow execution with sequential processes
    - Agent coordination and task assignment
    - Error handling and recovery for orchestration operations
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the CrewAI orchestration engine.

        Args:
            logger: Optional logger instance for engine operations
        """
        self.logger = logger or logging.getLogger(__name__)
        self.crew: Optional[Crew] = None
        self.agents: Dict[str, Agent] = {}
        self.workflows: Dict[str, Dict[str, Any]] = {}

        # Verify CrewAI availability
        try:
            import crewai

            self.crewai_version = crewai.__version__
            self.logger.info(
                f"CrewAI orchestration engine initialized with version {self.crewai_version}"
            )
        except ImportError as e:
            raise BmadCrewAIError(f"CrewAI not available: {e}") from e

    def initialize_crew(
        self, agents: List[Agent], process: Process = Process.sequential
    ) -> bool:
        """
        Initialize a CrewAI crew with the provided agents.

        Args:
            agents: List of CrewAI agents to include in the crew
            process: Process type for workflow execution (default: sequential)

        Returns:
            bool: True if crew initialized successfully, False otherwise
        """
        try:
            if not agents:
                self.logger.warning("No agents provided for crew initialization")
                return False

            self.crew = Crew(
                agents=agents,
                process=process,
                verbose=False,  # Reduce verbosity for production use
            )

            self.logger.info(
                f"CrewAI crew initialized with {len(agents)} agents using {process.value} process"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize CrewAI crew: {e}")
            return False

    def register_agent(self, agent_id: str, agent: Agent) -> bool:
        """
        Register a CrewAI agent with the orchestration engine.

        Args:
            agent_id: Unique identifier for the agent
            agent: CrewAI Agent instance

        Returns:
            bool: True if agent registered successfully, False otherwise
        """
        try:
            if not agent:
                self.logger.error(f"Cannot register agent {agent_id}: agent is None")
                return False

            if agent_id in self.agents:
                self.logger.warning(f"Agent {agent_id} already registered, overwriting")

            self.agents[agent_id] = agent
            self.logger.info(f"Agent {agent_id} registered successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """
        Get a registered agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)

    def list_agents(self) -> List[str]:
        """
        Get list of all registered agent IDs.

        Returns:
            List of agent IDs
        """
        return list(self.agents.keys())

    def execute_workflow(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Execute a workflow with the current crew.

        Args:
            tasks: List of CrewAI tasks to execute

        Returns:
            Dict containing execution results and status

        Raises:
            BmadCrewAIError: If crew is not initialized or execution fails
        """
        if not self.crew:
            raise BmadCrewAIError("Crew not initialized. Call initialize_crew() first.")

        if not tasks:
            raise BmadCrewAIError("No tasks provided for workflow execution")

        try:
            self.logger.info(f"Starting workflow execution with {len(tasks)} tasks")

            # Execute the workflow
            result = self.crew.kickoff(tasks)

            execution_result = {
                "status": "success",
                "result": result,
                "tasks_executed": len(tasks),
                "crew_size": len(self.agents) if self.agents else 0,
            }

            self.logger.info("Workflow execution completed successfully")
            return execution_result

        except Exception as e:
            error_msg = f"Workflow execution failed: {e}"
            self.logger.error(error_msg)

            return {
                "status": "error",
                "error": str(e),
                "tasks_attempted": len(tasks),
                "crew_size": len(self.agents) if self.agents else 0,
            }

    def create_task_from_spec(self, task_spec: Dict[str, Any]) -> Task:
        """
        Create a CrewAI task from a task specification.

        Args:
            task_spec: Dictionary containing task specifications
                Required keys: description, expected_output
                Optional keys: agent (agent_id), context, tools

        Returns:
            CrewAI Task instance

        Raises:
            BmadCrewAIError: If task specification is invalid
        """
        try:
            if not task_spec.get("description"):
                raise BmadCrewAIError("Task specification missing 'description'")

            if not task_spec.get("expected_output"):
                raise BmadCrewAIError("Task specification missing 'expected_output'")

            # Get agent if specified
            agent = None
            if task_spec.get("agent"):
                agent = self.get_agent(task_spec["agent"])
                if not agent:
                    self.logger.warning(
                        f"Agent {task_spec['agent']} not found, task will use crew default"
                    )

            # Create the task
            task = Task(
                description=task_spec["description"],
                expected_output=task_spec["expected_output"],
                agent=agent,
                context=task_spec.get("context"),
                tools=task_spec.get("tools", []),
            )

            return task

        except Exception as e:
            raise BmadCrewAIError(
                f"Failed to create task from specification: {e}"
            ) from e

    def get_engine_status(self) -> Dict[str, Any]:
        """
        Get the current status of the orchestration engine.

        Returns:
            Dict containing engine status information
        """
        return {
            "crewai_version": getattr(self, "crewai_version", "unknown"),
            "crew_initialized": self.crew is not None,
            "agents_registered": len(self.agents),
            "workflows_available": len(self.workflows),
            "agent_ids": list(self.agents.keys()),
        }

    def reset_engine(self) -> bool:
        """
        Reset the orchestration engine to initial state.

        Returns:
            bool: True if reset successful, False otherwise
        """
        try:
            self.crew = None
            self.agents.clear()
            self.workflows.clear()
            self.logger.info("CrewAI orchestration engine reset successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reset engine: {e}")
            return False
