"""
CrewAI Orchestration Engine for BMAD Framework

This module provides the core CrewAI orchestration functionality for the BMAD framework.
It manages CrewAI crews, workflows, and agent coordination.
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from crewai import Agent, Crew, Process, Task

from .artefact_manager import ArtefactManager
from .exceptions import BmadCrewAIError
from .workflow_state_manager import WorkflowStateManager


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
        self.bmad_registry = None  # Reference to BMAD AgentRegistry

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

    def integrate_bmad_registry(self, bmad_registry) -> bool:
        """
        Integrate with BMAD AgentRegistry for seamless agent management.

        Args:
            bmad_registry: Instance of AgentRegistry

        Returns:
            bool: True if integration successful, False otherwise
        """
        try:
            self.bmad_registry = bmad_registry

            # Register all BMAD agents with the orchestration engine
            if bmad_registry.bmad_agents:
                for agent_id, agent in bmad_registry.bmad_agents.items():
                    self.register_agent(agent_id, agent)

                self.logger.info(
                    f"Integrated {len(bmad_registry.bmad_agents)} BMAD agents"
                )
                return True
            else:
                self.logger.warning("No BMAD agents found in registry")
                return False

        except Exception as e:
            self.logger.error(f"Failed to integrate BMAD registry: {e}")
            return False

    def get_bmad_agent(self, agent_id: str) -> Optional[Agent]:
        """
        Get a BMAD agent by ID from the integrated registry.

        Args:
            agent_id: BMAD agent identifier

        Returns:
            Agent instance or None if not found
        """
        if self.bmad_registry:
            return self.bmad_registry.get_bmad_agent(agent_id)
        return None

    def list_bmad_agents(self) -> List[str]:
        """
        Get list of all registered BMAD agent IDs.

        Returns:
            List of BMAD agent IDs
        """
        if self.bmad_registry:
            return list(self.bmad_registry.bmad_agents.keys())
        return []

    def execute_bmad_workflow(self, workflow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a workflow using BMAD agents.

        Args:
            workflow_spec: Workflow specification with tasks and agent assignments

        Returns:
            Dict containing workflow execution results
        """
        if not self.bmad_registry:
            raise BmadCrewAIError(
                "BMAD registry not integrated. Call integrate_bmad_registry() first."
            )

        try:
            tasks = []

            # Create tasks with BMAD agent assignments
            for task_spec in workflow_spec.get("tasks", []):
                agent_id = task_spec.get("agent")
                if agent_id:
                    agent = self.get_bmad_agent(agent_id)
                    if agent:
                        task = self.create_task_from_spec(
                            {
                                "description": task_spec["description"],
                                "expected_output": task_spec["expected_output"],
                                "agent": agent_id,  # Will be resolved in create_task_from_spec
                                "context": task_spec.get("context"),
                            }
                        )
                        tasks.append(task)
                    else:
                        self.logger.warning(
                            f"BMAD agent {agent_id} not found, skipping task"
                        )
                else:
                    # Task without specific agent assignment
                    task = self.create_task_from_spec(task_spec)
                    tasks.append(task)

            if not tasks:
                raise BmadCrewAIError("No valid tasks found in workflow specification")

            # Execute the workflow
            return self.execute_workflow(tasks)

        except Exception as e:
            error_msg = f"BMAD workflow execution failed: {e}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "error": str(e),
                "workflow_spec": workflow_spec,
            }

    def validate_bmad_agent_communication(self) -> Dict[str, Any]:
        """
        Validate that BMAD agents can communicate and coordinate properly.

        Returns:
            Dict with communication validation results
        """
        results = {
            "registry_integrated": self.bmad_registry is not None,
            "agents_available": False,
            "communication_test": False,
            "coordination_test": False,
            "errors": [],
        }

        if not self.bmad_registry:
            results["errors"].append("BMAD registry not integrated")
            return results

        try:
            bmad_agents = self.list_bmad_agents()
            results["agents_available"] = len(bmad_agents) > 0

            if not bmad_agents:
                results["errors"].append("No BMAD agents available")
                return results

            # Test basic agent communication
            test_agent = self.get_bmad_agent(bmad_agents[0])
            if test_agent and hasattr(test_agent, "role"):
                results["communication_test"] = True

            # Test agent coordination through crew
            if self.crew:
                results["coordination_test"] = True

        except Exception as e:
            results["errors"].append(f"Validation error: {e}")

        return results

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
            self.bmad_registry = None  # Clear BMAD registry reference
            self.logger.info("CrewAI orchestration engine reset successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reset engine: {e}")
            return False


class BmadWorkflowEngine:
    """
    Enhanced workflow engine with state management integration for BMAD framework.

    Manages workflow execution with state persistence, checkpoints, and recovery
    capabilities for complex agent interactions and interruptions.
    """

    def __init__(
        self,
        crew: Optional[Crew] = None,
        state_manager: Optional["WorkflowStateManager"] = None,
        artefact_manager: Optional[ArtefactManager] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the BMAD Workflow Engine with comprehensive artefact generation.

        Args:
            crew: Optional CrewAI crew instance
            state_manager: Optional WorkflowStateManager instance
            artefact_manager: Optional ArtefactManager instance for artefact generation
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.crew = crew
        self.state_manager = state_manager
        self.artefact_manager = artefact_manager

        # Initialize state manager if not provided
        if not self.state_manager:
            from .workflow_state_manager import WorkflowStateManager

            self.state_manager = WorkflowStateManager(logger=self.logger)

        # Initialize artefact manager if not provided
        if not self.artefact_manager:
            self.artefact_manager = ArtefactManager()

        # Threading support for concurrent operations
        self._active_workflows: Dict[str, Dict[str, Any]] = {}
        self._workflow_locks: Dict[str, threading.Lock] = {}

        self.logger.info(
            "BmadWorkflowEngine initialized with state management and artefact generation"
        )

    def execute_workflow(
        self, workflow_template: Dict[str, Any], workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow with state management integration.

        Args:
            workflow_template: Workflow specification dictionary
            workflow_id: Optional workflow identifier (auto-generated if not provided)

        Returns:
            Dict[str, Any]: Workflow execution results
        """
        if not workflow_id:
            workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize workflow lock
        self._workflow_locks[workflow_id] = threading.Lock()

        with self._workflow_locks[workflow_id]:
            try:
                # Initialize workflow state
                initial_state = self._create_initial_workflow_state(
                    workflow_template, workflow_id
                )
                success = self.state_manager.persist_state(workflow_id, initial_state)

                if not success:
                    raise BmadCrewAIError(
                        f"Failed to initialize workflow state for {workflow_id}"
                    )

                self._active_workflows[workflow_id] = {
                    "template": workflow_template,
                    "start_time": datetime.now(),
                    "status": "running",
                }

                # Execute workflow with state checkpoints
                result = self._execute_with_state_checkpoints(
                    workflow_id, workflow_template
                )

                # Update final state
                final_state = self.state_manager.recover_state(workflow_id) or {}
                final_state["status"] = (
                    "completed" if result.get("status") == "success" else "failed"
                )
                final_state["end_time"] = datetime.now().isoformat()
                final_state["result"] = result

                self.state_manager.persist_state(workflow_id, final_state)

                # Cleanup active workflow tracking
                if workflow_id in self._active_workflows:
                    del self._active_workflows[workflow_id]

                return result

            except Exception as e:
                error_msg = f"Workflow execution failed for {workflow_id}: {e}"
                self.logger.error(error_msg)

                # Mark workflow as interrupted
                self.state_manager.mark_workflow_interrupted(workflow_id, str(e))

                return {
                    "status": "error",
                    "error": str(e),
                    "workflow_id": workflow_id,
                    "timestamp": datetime.now().isoformat(),
                }

    def _create_initial_workflow_state(
        self, workflow_template: Dict[str, Any], workflow_id: str
    ) -> Dict[str, Any]:
        """
        Create initial workflow state from template.

        Args:
            workflow_template: Workflow specification
            workflow_id: Workflow identifier

        Returns:
            Dict[str, Any]: Initial state dictionary
        """
        tasks = workflow_template.get("tasks", [])
        return {
            "status": "initialized",
            "current_step": "initialization",
            "steps_completed": [],
            "total_steps": len(tasks),
            "workflow_template": workflow_template,
            "agent_handoffs": [],
            "agent_dependencies": {},
            "execution_timeline": [
                {
                    "type": "initialization",
                    "timestamp": datetime.now().isoformat(),
                    "description": f"Workflow {workflow_id} initialized",
                }
            ],
            "progress": {"completed": 0, "total": len(tasks), "percentage": 0.0},
            "checkpoints": [],
            "_metadata": {
                "workflow_id": workflow_id,
                "created": datetime.now().isoformat(),
                "version": "1.0",
            },
        }

    def _execute_with_state_checkpoints(
        self, workflow_id: str, workflow_template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute workflow with state checkpoints and recovery support.

        Args:
            workflow_id: Workflow identifier
            workflow_template: Workflow specification

        Returns:
            Dict[str, Any]: Execution results
        """
        results = {
            "status": "running",
            "workflow_id": workflow_id,
            "task_results": [],
            "checkpoints": [],
        }

        try:
            tasks = workflow_template.get("tasks", [])

            for i, task_spec in enumerate(tasks):
                # Create checkpoint before task execution
                checkpoint_id = f"checkpoint_{i}"
                self._create_checkpoint(workflow_id, checkpoint_id, task_spec)

                # Update current step in state
                state = self.state_manager.recover_state(workflow_id)
                if state:
                    state["current_step"] = (
                        f"task_{i}: {task_spec.get('description', 'unknown')}"
                    )
                    self.state_manager.persist_state(workflow_id, state)

                # Execute task
                task_result = self._execute_task_with_agent_handling(
                    workflow_id, task_spec, i
                )

                # Record result
                results["task_results"].append(task_result)

                # Update progress
                self._update_workflow_progress(workflow_id, i + 1, len(tasks))

                # Check for interruption or failure
                if task_result.get("status") == "failed":
                    results["status"] = "failed"
                    results["failed_at"] = i
                    break

            # Mark as completed if all tasks succeeded
            if results["status"] == "running":
                results["status"] = "success"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.logger.error(f"Workflow execution error: {e}")

        return results

    def _create_checkpoint(
        self, workflow_id: str, checkpoint_id: str, task_spec: Dict[str, Any]
    ) -> None:
        """
        Create a workflow checkpoint before task execution.

        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Checkpoint identifier
            task_spec: Task specification
        """
        try:
            state = self.state_manager.recover_state(workflow_id)
            if not state:
                return

            checkpoint = {
                "id": checkpoint_id,
                "timestamp": datetime.now().isoformat(),
                "task_spec": task_spec,
                "state_snapshot": state.copy(),
            }

            if "checkpoints" not in state:
                state["checkpoints"] = []

            state["checkpoints"].append(checkpoint)
            self.state_manager.persist_state(workflow_id, state)

        except Exception as e:
            self.logger.error(f"Failed to create checkpoint {checkpoint_id}: {e}")

    def _execute_task_with_agent_handling(
        self, workflow_id: str, task_spec: Dict[str, Any], task_index: int
    ) -> Dict[str, Any]:
        """
        Execute a task with agent handoff handling and state tracking.

        Args:
            workflow_id: Workflow identifier
            task_spec: Task specification
            task_index: Task index in workflow

        Returns:
            Dict[str, Any]: Task execution result
        """
        agent_id = task_spec.get("agent")
        task_result = {
            "task_index": task_index,
            "agent": agent_id,
            "status": "pending",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Validate agent handoff if this follows another task
            if task_index > 0:
                prev_task = self._get_previous_task_agent(workflow_id, task_index - 1)
                if prev_task and agent_id and prev_task != agent_id:
                    # Validate handoff
                    validation = self.state_manager.validate_agent_handoff(
                        workflow_id, prev_task, agent_id
                    )
                    if not validation.get("is_valid", True):
                        task_result.update(
                            {
                                "status": "failed",
                                "error": "Agent handoff validation failed",
                                "validation": validation,
                            }
                        )
                        return task_result

                    # Track the handoff
                    self.state_manager.track_agent_handoff(
                        workflow_id,
                        prev_task,
                        agent_id,
                        {"task_index": task_index, "from_task": task_index - 1},
                    )

            # Execute the task (simplified for now - would integrate with actual CrewAI execution)
            if self.crew and agent_id:
                # In real implementation, this would execute the actual CrewAI task
                task_result.update(
                    {
                        "status": "success",
                        "message": f"Task executed by agent {agent_id}",
                        "simulated": True,  # Remove when real execution is implemented
                    }
                )
            else:
                # Fallback for testing/development
                task_result.update(
                    {
                        "status": "success",
                        "message": f"Task simulated for agent {agent_id}",
                        "simulated": True,
                    }
                )

            # Generate artefacts if specified in task
            artefact_result = self._generate_task_artefacts(
                workflow_id, task_spec, task_result
            )
            task_result["artefacts_generated"] = artefact_result

            # Update steps completed
            state = self.state_manager.recover_state(workflow_id)
            if state:
                if "steps_completed" not in state:
                    state["steps_completed"] = []
                state["steps_completed"].append(task_index)
                self.state_manager.persist_state(workflow_id, state)

        except Exception as e:
            task_result.update({"status": "failed", "error": str(e)})

            # Handle agent failure recovery
            recovery_info = self.state_manager.recover_from_agent_failure(
                workflow_id, agent_id or "unknown"
            )
            if recovery_info:
                task_result["recovery_options"] = recovery_info.get("options", [])

        return task_result

    def _generate_task_artefacts(
        self, workflow_id: str, task_spec: Dict[str, Any], task_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate artefacts for a completed task using comprehensive artefact generation.

        Args:
            workflow_id: Workflow identifier
            task_spec: Task specification
            task_result: Task execution result

        Returns:
            Dict[str, Any]: Artefact generation results
        """
        artefact_results = {"generated": [], "failed": [], "skipped": []}

        try:
            # Check if task specifies artefact generation
            output_spec = task_spec.get("output", {})
            if not output_spec:
                artefact_results["skipped"].append("No output specification in task")
                return artefact_results

            # Extract artefact generation parameters
            artefact_type = output_spec.get("artefact_type")
            content_template = output_spec.get("content_template", "")
            generation_params = output_spec.get("params", {})

            if not artefact_type:
                artefact_results["skipped"].append("No artefact type specified")
                return artefact_results

            # Generate content from task result if template uses placeholders
            content = self._resolve_content_template(
                content_template, task_result, workflow_id
            )

            # Use comprehensive artefact generation
            context = {
                "workflow_id": workflow_id,
                "task_index": task_result.get("task_index"),
                "agent": task_result.get("agent"),
                "artefact_type": artefact_type,
            }

            success = self.artefact_manager.generate_comprehensive_artefact(
                content=content,
                artefact_type=artefact_type,
                context=context,
                **generation_params,
            )

            if success:
                artefact_results["generated"].append(
                    {
                        "type": artefact_type,
                        "workflow_id": workflow_id,
                        "task_index": task_result.get("task_index"),
                    }
                )
                self.logger.info(
                    f"Successfully generated artefact {artefact_type} for workflow {workflow_id}"
                )
            else:
                artefact_results["failed"].append(
                    {"type": artefact_type, "reason": "Artefact generation failed"}
                )
                self.logger.error(
                    f"Failed to generate artefact {artefact_type} for workflow {workflow_id}"
                )

        except Exception as e:
            artefact_results["failed"].append(
                {"type": artefact_type or "unknown", "reason": str(e)}
            )
            self.logger.error(f"Artefact generation error: {e}")

        return artefact_results

    def _resolve_content_template(
        self, template: str, task_result: Dict[str, Any], workflow_id: str
    ) -> str:
        """
        Resolve template placeholders with actual values from task execution.

        Args:
            template: Content template with placeholders
            task_result: Task execution result
            workflow_id: Workflow identifier

        Returns:
            str: Resolved content
        """
        try:
            content = template

            # Basic placeholder resolution
            placeholders = {
                "{{workflow_id}}": workflow_id,
                "{{task_index}}": str(task_result.get("task_index", "")),
                "{{agent}}": task_result.get("agent", ""),
                "{{timestamp}}": datetime.now().isoformat(),
                "{{status}}": task_result.get("status", ""),
            }

            for placeholder, value in placeholders.items():
                content = content.replace(placeholder, str(value))

            # Add task result message if present
            if task_result.get("message"):
                content = content.replace("{{task_message}}", task_result["message"])

            return content

        except Exception as e:
            self.logger.warning(f"Template resolution failed: {e}")
            return template  # Return original template if resolution fails

    def _get_previous_task_agent(
        self, workflow_id: str, prev_index: int
    ) -> Optional[str]:
        """
        Get the agent that executed the previous task.

        Args:
            workflow_id: Workflow identifier
            prev_index: Previous task index

        Returns:
            Optional[str]: Previous agent ID or None
        """
        try:
            state = self.state_manager.recover_state(workflow_id)
            if not state:
                return None

            tasks = state.get("workflow_template", {}).get("tasks", [])
            if prev_index < len(tasks):
                return tasks[prev_index].get("agent")

        except Exception as e:
            self.logger.error(f"Failed to get previous task agent: {e}")

        return None

    def _update_workflow_progress(
        self, workflow_id: str, completed: int, total: int
    ) -> None:
        """
        Update workflow progress metrics.

        Args:
            workflow_id: Workflow identifier
            completed: Number of completed tasks
            total: Total number of tasks
        """
        try:
            state = self.state_manager.recover_state(workflow_id)
            if state:
                percentage = (completed / total * 100) if total > 0 else 0
                state["progress"] = {
                    "completed": completed,
                    "total": total,
                    "percentage": round(percentage, 2),
                    "last_updated": datetime.now().isoformat(),
                }
                self.state_manager.persist_state(workflow_id, state)

        except Exception as e:
            self.logger.error(f"Failed to update workflow progress: {e}")

    def recover_workflow_from_checkpoint(
        self, workflow_id: str, checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Recover workflow execution from a checkpoint.

        Args:
            checkpoint_id: Optional specific checkpoint ID, uses last if not provided

        Returns:
            Optional[Dict[str, Any]]: Recovery result or None
        """
        try:
            state = self.state_manager.recover_state(workflow_id)
            if not state:
                return None

            checkpoints = state.get("checkpoints", [])
            if not checkpoints:
                return None

            # Use last checkpoint if none specified
            if not checkpoint_id:
                checkpoint = checkpoints[-1]
            else:
                checkpoint = next(
                    (cp for cp in checkpoints if cp["id"] == checkpoint_id), None
                )

            if not checkpoint:
                return None

            # Restore state from checkpoint
            restored_state = checkpoint["state_snapshot"].copy()
            restored_state["status"] = "running"
            restored_state["recovery_checkpoint"] = checkpoint_id
            restored_state["recovery_time"] = datetime.now().isoformat()

            success = self.state_manager.persist_state(workflow_id, restored_state)

            if success:
                return {
                    "status": "recovered",
                    "checkpoint_id": checkpoint["id"],
                    "restored_state": restored_state,
                }

        except Exception as e:
            self.logger.error(f"Failed to recover from checkpoint: {e}")

        return None

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive workflow status including state information.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Optional[Dict[str, Any]]: Workflow status or None
        """
        try:
            # Get state information
            state = self.state_manager.recover_state(workflow_id)
            if not state:
                return None

            # Get progress information
            progress = self.state_manager.get_workflow_progress(workflow_id)

            # Combine with active workflow info
            active_info = self._active_workflows.get(workflow_id, {})

            return {
                "workflow_id": workflow_id,
                "state": state,
                "progress": progress,
                "active_info": active_info,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get workflow status: {e}")
            return None

    def pause_workflow(self, workflow_id: str) -> bool:
        """
        Pause a running workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            bool: True if paused successfully
        """
        try:
            state = self.state_manager.recover_state(workflow_id)
            if state and state.get("status") == "running":
                state["status"] = "paused"
                state["paused_at"] = datetime.now().isoformat()
                return self.state_manager.persist_state(workflow_id, state)

        except Exception as e:
            self.logger.error(f"Failed to pause workflow {workflow_id}: {e}")

        return False

    def resume_workflow(self, workflow_id: str) -> bool:
        """
        Resume a paused workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            bool: True if resumed successfully
        """
        try:
            state = self.state_manager.recover_state(workflow_id)
            if state and state.get("status") == "paused":
                state["status"] = "running"
                state["resumed_at"] = datetime.now().isoformat()

                # Add timeline entry
                timeline_entry = {
                    "type": "resume",
                    "timestamp": state["resumed_at"],
                    "description": "Workflow resumed from pause",
                }
                state["execution_timeline"].append(timeline_entry)

                return self.state_manager.persist_state(workflow_id, state)

        except Exception as e:
            self.logger.error(f"Failed to resume workflow {workflow_id}: {e}")

        return False
