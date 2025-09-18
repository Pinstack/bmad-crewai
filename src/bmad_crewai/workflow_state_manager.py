"""
Workflow State Management for BMAD Framework

This module provides state persistence, recovery, and tracking capabilities
for complex workflow execution with agent handoffs and interruptions.
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class WorkflowStateManager:
    """
    Manages workflow state persistence and recovery for BMAD framework.

    Handles:
    - State serialization using JSON format for local storage
    - State validation and corruption handling
    - Recovery mechanism for interrupted workflows
    - Agent handoff tracking and dependency management
    - Progress monitoring with status updates
    - Concurrent agent operation support with state synchronization
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        storage_dir: str = ".bmad-workflows",
    ):
        """
        Initialize the WorkflowStateManager.

        Args:
            logger: Optional logger instance
            storage_dir: Directory for state persistence (default: .bmad-workflows)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

        # Thread safety for concurrent operations
        self._lock = threading.RLock()
        self._active_workflows: Set[str] = set()

        # Metrics storage for monitoring and analytics
        self.metrics_storage = {}
        self.performance_history = {}

        # Retention policy configuration
        self.retention_policies = {
            "max_age_days": 30,
            "max_entries_per_workflow": 100,
            "compression_threshold_days": 7,
            "auto_cleanup_interval_hours": 24,
            "storage_limit_mb": 100,
        }

        # Cleanup scheduling
        self.last_cleanup = datetime.now()
        self.cleanup_enabled = True

        self.logger.info(
            f"WorkflowStateManager initialized with storage dir: {storage_dir}"
        )

    def persist_state(self, workflow_id: str, state_dict: Dict[str, Any]) -> bool:
        """
        Persist workflow state to local JSON file.

        Args:
            workflow_id: Unique workflow identifier
            state_dict: State dictionary to persist

        Returns:
            bool: True if persistence successful, False otherwise
        """
        with self._lock:
            try:
                if not state_dict:
                    return False
                # Start with a shallow copy so we can safely enrich without mutating caller's dict
                working = dict(state_dict or {})

                # Fill in sensible defaults for required fields
                working.setdefault("status", "initialized")
                working.setdefault("current_step", "unknown")
                working.setdefault("steps_completed", [])

                # Create a clean, serializable state dictionary (shallow filter of top-level types)
                clean_state: Dict[str, Any] = {}
                for key, value in working.items():
                    if isinstance(
                        value, (str, int, float, bool, type(None), dict, list)
                    ):
                        clean_state[key] = value

                # Add/update metadata
                enriched_state = {
                    **clean_state,
                    "_metadata": {
                        "workflow_id": workflow_id,
                        "timestamp": datetime.now().isoformat(),
                        "version": "1.0",
                    },
                }

                # Validate (after defaults were applied)
                if not self._validate_state_structure(enriched_state):
                    self.logger.error(
                        f"Invalid state structure for workflow {workflow_id}"
                    )
                    return False

                state_file = self.storage_dir / f"{workflow_id}.json"

                # Merge with existing state to preserve concurrent counters
                existing_state = {}
                if state_file.exists():
                    try:
                        existing_state = json.load(
                            open(state_file, "r", encoding="utf-8")
                        )
                    except Exception:
                        existing_state = {}

                # Special handling for concurrent counters (only when updating an existing state)
                if state_file.exists() and "concurrent_access_count" in enriched_state:
                    try:
                        existing_count = int(
                            existing_state.get("concurrent_access_count", 0)
                        )
                        incoming_count = int(
                            enriched_state.get("concurrent_access_count", 0)
                        )
                        enriched_state["concurrent_access_count"] = max(
                            incoming_count, existing_count + 1
                        )
                    except Exception:
                        pass

                with open(state_file, "w", encoding="utf-8") as f:
                    try:
                        json.dump(enriched_state, f, indent=2, ensure_ascii=False)
                    except (TypeError, ValueError) as e:
                        self.logger.error(
                            f"JSON serialization error for workflow {workflow_id}: {e}"
                        )
                        # Fallback to sanitized JSON (removes non-serializable/cycles)
                        sanitized_state = self._sanitize_for_json(enriched_state)
                        json.dump(sanitized_state, f, indent=2, ensure_ascii=False)

                self.logger.info(f"Workflow state persisted for {workflow_id}")
                return True

            except Exception as e:
                self.logger.error(
                    f"Failed to persist state for workflow {workflow_id}: {e}"
                )
                return False

    def _sanitize_for_json(self, data: Any, _seen: Optional[set] = None) -> Any:
        """Recursively sanitize a Python object for safe JSON serialization.

        - Removes circular references
        - Converts unsupported types to strings
        - Truncates deeply nested structures in a conservative way
        """
        if _seen is None:
            _seen = set()

        try:
            obj_id = id(data)
            if obj_id in _seen:
                return "<circular>"
            _seen.add(obj_id)
        except Exception:
            # If an object is not hashable, skip cycle tracking for it
            pass

        if isinstance(data, (str, int, float, bool)) or data is None:
            return data
        if isinstance(data, dict):
            return {str(k): self._sanitize_for_json(v, _seen) for k, v in data.items()}
        if isinstance(data, list):
            return [self._sanitize_for_json(v, _seen) for v in data]
        if isinstance(data, tuple):
            return [self._sanitize_for_json(v, _seen) for v in data]

        # Fallback: represent as string
        return str(data)

    def recover_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Load and validate workflow state from storage.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            Optional[Dict[str, Any]]: Recovered state dict or None if recovery fails
        """
        with self._lock:
            try:
                state_file = self.storage_dir / f"{workflow_id}.json"

                if not state_file.exists():
                    self.logger.warning(
                        f"No state file found for workflow {workflow_id}"
                    )
                    return None

                with open(state_file, "r", encoding="utf-8") as f:
                    state_data = json.load(f)

                # Validate loaded state
                if not self._validate_state_structure(state_data):
                    self.logger.error(
                        f"Corrupted state file for workflow {workflow_id}"
                    )
                    # Attempt recovery by creating backup and returning minimal state
                    self._handle_corrupted_state(workflow_id, state_data)
                    return self._create_minimal_recovery_state(workflow_id)

                self.logger.info(f"Workflow state recovered for {workflow_id}")
                return state_data

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for workflow {workflow_id}: {e}")
                # Backup corrupted file contents for diagnostics
                try:
                    state_file = self.storage_dir / f"{workflow_id}.json"
                    raw = (
                        state_file.read_text(encoding="utf-8")
                        if state_file.exists()
                        else ""
                    )
                    self._handle_corrupted_state(workflow_id, {"raw": raw})
                except Exception:
                    pass
                return self._create_minimal_recovery_state(workflow_id)
            except Exception as e:
                self.logger.error(
                    f"Failed to recover state for workflow {workflow_id}: {e}"
                )
                return None

    def _validate_state_structure(self, state_dict: Dict[str, Any]) -> bool:
        """
        Validate the structure of a workflow state dictionary.

        Args:
            state_dict: State dictionary to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check for required metadata
            if "_metadata" not in state_dict:
                return False

            metadata = state_dict["_metadata"]
            required_meta_fields = ["workflow_id", "timestamp", "version"]
            if not all(field in metadata for field in required_meta_fields):
                return False

            # Check for basic workflow state fields
            required_fields = ["status", "current_step", "steps_completed"]
            if not all(field in state_dict for field in required_fields):
                return False

            # Validate status values
            valid_statuses = [
                "initialized",
                "running",
                "paused",
                "completed",
                "failed",
                "interrupted",
            ]
            if state_dict.get("status") not in valid_statuses:
                return False

            return True

        except Exception as e:
            self.logger.error(f"State validation error: {e}")
            return False

    def _handle_corrupted_state(
        self, workflow_id: str, corrupted_data: Dict[str, Any]
    ) -> None:
        """
        Handle corrupted state files by creating backups.

        Args:
            workflow_id: Workflow identifier
            corrupted_data: The corrupted state data
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.storage_dir / f"{workflow_id}_corrupted_{timestamp}.json"

            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(corrupted_data, f, indent=2, ensure_ascii=False)

            self.logger.warning(f"Corrupted state backed up to {backup_file}")

        except Exception as e:
            self.logger.error(f"Failed to backup corrupted state: {e}")

    def _create_minimal_recovery_state(self, workflow_id: str) -> Dict[str, Any]:
        """
        Create a minimal recovery state for corrupted workflows.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dict[str, Any]: Minimal recovery state
        """
        return {
            "status": "interrupted",
            "current_step": "recovery",
            "steps_completed": [],
            "agent_handoffs": [],
            "progress": {"completed": 0, "total": 0, "percentage": 0},
            "_metadata": {
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "recovered": True,
            },
        }

    def track_agent_handoff(
        self,
        workflow_id: str,
        from_agent: str,
        to_agent: str,
        handoff_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Track agent handoffs and dependencies in workflow state.

        Args:
            workflow_id: Workflow identifier
            from_agent: Agent handing off
            to_agent: Agent receiving handoff
            handoff_data: Optional data associated with handoff

        Returns:
            bool: True if tracking successful, False otherwise
        """
        with self._lock:
            try:
                state = self.recover_state(workflow_id)
                if not state:
                    self.logger.error(
                        f"Cannot track handoff for non-existent workflow {workflow_id}"
                    )
                    return False

                # Initialize handoff tracking structures
                if "agent_handoffs" not in state:
                    state["agent_handoffs"] = []

                if "agent_dependencies" not in state:
                    state["agent_dependencies"] = {}

                if "execution_timeline" not in state:
                    state["execution_timeline"] = []

                # Create handoff record
                handoff_record = {
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "timestamp": datetime.now().isoformat(),
                    "sequence_id": len(state["agent_handoffs"]),
                    "data": handoff_data or {},
                    "status": "completed",
                }

                state["agent_handoffs"].append(handoff_record)

                # Update dependencies
                if from_agent not in state["agent_dependencies"]:
                    state["agent_dependencies"][from_agent] = []

                if to_agent not in state["agent_dependencies"][from_agent]:
                    state["agent_dependencies"][from_agent].append(to_agent)

                # Add to execution timeline
                timeline_entry = {
                    "type": "handoff",
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "timestamp": handoff_record["timestamp"],
                    "description": f"Agent handoff: {from_agent} → {to_agent}",
                }
                if "execution_timeline" not in state:
                    state["execution_timeline"] = []
                state["execution_timeline"].append(timeline_entry)

                # Update progress monitoring
                self._update_progress_metrics(state)

                return self.persist_state(workflow_id, state)

            except Exception as e:
                self.logger.error(
                    f"Failed to track agent handoff for {workflow_id}: {e}"
                )
                return False

    def _update_progress_metrics(self, state: Dict[str, Any]) -> None:
        """
        Update progress monitoring metrics in the workflow state.

        Args:
            state: Workflow state dictionary to update
        """
        try:
            steps_completed = len(state.get("steps_completed", []))
            total_steps = state.get("total_steps", max(steps_completed, 1))

            # Calculate progress percentage
            percentage = (
                min(100, (steps_completed / total_steps) * 100)
                if total_steps > 0
                else 0
            )

            # Update progress structure
            if "progress" not in state:
                state["progress"] = {}

            state["progress"].update(
                {
                    "completed": steps_completed,
                    "total": total_steps,
                    "percentage": round(percentage, 2),
                    "last_updated": datetime.now().isoformat(),
                }
            )

            # Update status based on progress
            if state.get("status") == "running":
                if percentage >= 100:
                    state["status"] = "completed"
                elif state.get("interruption_reason"):
                    state["status"] = "interrupted"

        except Exception as e:
            self.logger.error(f"Failed to update progress metrics: {e}")

    def get_workflow_progress(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get progress monitoring information for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Optional[Dict[str, Any]]: Progress information or None
        """
        with self._lock:
            try:
                state = self.recover_state(workflow_id)
                if not state:
                    return None

                progress_info = {
                    "status": state.get("status", "unknown"),
                    "current_step": state.get("current_step", "unknown"),
                    "steps_completed": len(state.get("steps_completed", [])),
                    "total_steps": state.get("total_steps", 0),
                    "percentage": state.get("progress", {}).get("percentage", 0),
                    "last_updated": state.get("_metadata", {}).get("timestamp"),
                    "agent_handoffs": len(state.get("agent_handoffs", [])),
                    "execution_timeline_entries": len(
                        state.get("execution_timeline", [])
                    ),
                }

                # Add timeline summary if available
                timeline = state.get("execution_timeline", [])
                if timeline:
                    progress_info["last_activity"] = timeline[-1].get("timestamp")
                    progress_info["recent_activities"] = timeline[
                        -3:
                    ]  # Last 3 activities

                return progress_info

            except Exception as e:
                self.logger.error(f"Failed to get progress for {workflow_id}: {e}")
                return None

    def mark_workflow_interrupted(
        self, workflow_id: str, reason: str = "unknown"
    ) -> bool:
        """
        Mark a workflow as interrupted for recovery handling.

        Args:
            workflow_id: Workflow identifier
            reason: Reason for interruption

        Returns:
            bool: True if marked successfully, False otherwise
        """
        with self._lock:
            try:
                state = self.recover_state(workflow_id)
                if not state:
                    # Create minimal interrupted state
                    state = self._create_minimal_recovery_state(workflow_id)

                state["status"] = "interrupted"
                state["interruption_reason"] = reason
                state["interruption_time"] = datetime.now().isoformat()

                return self.persist_state(workflow_id, state)

            except Exception as e:
                self.logger.error(
                    f"Failed to mark workflow {workflow_id} as interrupted: {e}"
                )
                return False

    def cleanup_workflow_state(self, workflow_id: str) -> bool:
        """
        Clean up workflow state files after completion.

        Args:
            workflow_id: Workflow identifier

        Returns:
            bool: True if cleanup successful, False otherwise
        """
        with self._lock:
            try:
                state_file = self.storage_dir / f"{workflow_id}.json"
                if state_file.exists():
                    state_file.unlink()
                    self.logger.info(f"Workflow state cleaned up for {workflow_id}")
                    return True
                return False

            except Exception as e:
                self.logger.error(f"Failed to cleanup state for {workflow_id}: {e}")
                return False

    def list_active_workflows(self) -> List[str]:
        """
        List all active workflows based on state files.

        Returns:
            List[str]: List of active workflow IDs
        """
        try:
            workflow_files = self.storage_dir.glob("*.json")
            active_workflows = []

            for wf_file in workflow_files:
                if wf_file.name.endswith("_corrupted_"):
                    continue  # Skip backup files

                workflow_id = wf_file.stem
                state = self.recover_state(workflow_id)
                if state and state.get("status") in [
                    "initialized",
                    "running",
                    "paused",
                    "interrupted",
                ]:
                    active_workflows.append(workflow_id)

            return active_workflows

        except Exception as e:
            self.logger.error(f"Failed to list active workflows: {e}")
            return []

    def validate_agent_handoff(
        self, workflow_id: str, from_agent: str, to_agent: str
    ) -> Dict[str, Any]:
        """
        Validate agent handoff before execution.

        Args:
            workflow_id: Workflow identifier
            from_agent: Agent handing off
            to_agent: Agent receiving handoff

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
            state = self.recover_state(workflow_id)
            if not state:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Workflow state not found")
                return validation_result

            # Check if workflow is in valid state for handoff
            current_status = state.get("status")
            if current_status not in ["running", "initialized"]:
                validation_result["warnings"].append(
                    f"Workflow status is {current_status}, handoff may not be expected"
                )

            # Check agent dependencies
            dependencies = state.get("agent_dependencies", {})
            if from_agent in dependencies:
                expected_targets = dependencies[from_agent]
                if to_agent not in expected_targets:
                    validation_result["warnings"].append(
                        f"Unexpected handoff: {from_agent} → {to_agent}"
                    )

            # Check for circular dependencies
            if self._has_circular_dependency(state, from_agent, to_agent):
                validation_result["is_valid"] = False
                validation_result["errors"].append(
                    f"Circular dependency detected: {from_agent} ↔ {to_agent}"
                )

            # Check agent handoff history for patterns
            handoffs = state.get("agent_handoffs", [])
            recent_handoffs = [
                h
                for h in handoffs
                if h.get("from_agent") == from_agent and h.get("to_agent") == to_agent
            ]
            if len(recent_handoffs) > 5:
                validation_result["warnings"].append(
                    f"Frequent handoffs between {from_agent} and {to_agent} detected"
                )

            # Validate handoff data structure
            if "agent_handoffs" not in state:
                validation_result["recommendations"].append(
                    "Initialize agent_handoffs structure in state"
                )

        except Exception as e:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")

        return validation_result

    def _has_circular_dependency(
        self, state: Dict[str, Any], from_agent: str, to_agent: str
    ) -> bool:
        """
        Check for circular dependencies in agent handoffs.

        Args:
            state: Workflow state
            from_agent: Agent handing off
            to_agent: Agent receiving handoff

        Returns:
            bool: True if circular dependency detected
        """
        try:
            dependencies = state.get("agent_dependencies", {})

            # Check if to_agent already depends on from_agent
            if to_agent in dependencies and from_agent in dependencies[to_agent]:
                return True

            # Check deeper circular paths (simplified check)
            visited = set()
            to_check = [to_agent]

            while to_check:
                current = to_check.pop()
                if current in visited:
                    continue
                visited.add(current)

                if current in dependencies:
                    deps = dependencies[current]
                    if from_agent in deps:
                        return True
                    to_check.extend(deps)

            return False

        except Exception:
            return False  # Conservative approach

    def recover_from_agent_failure(
        self, workflow_id: str, failed_agent: str
    ) -> Optional[Dict[str, Any]]:
        """
        Recover workflow state from agent failure.

        Args:
            workflow_id: Workflow identifier
            failed_agent: Agent that failed

        Returns:
            Optional[Dict[str, Any]]: Recovery state or None
        """
        with self._lock:
            try:
                state = self.recover_state(workflow_id)
                if not state:
                    # Initialize a minimal state to proceed with recovery
                    state = {
                        "status": "interrupted",
                        "current_step": "unknown",
                        "steps_completed": [],
                        "agent_handoffs": [],
                        "execution_timeline": [],
                    }

                # Mark workflow as interrupted
                state["status"] = "interrupted"
                state["failure_agent"] = failed_agent
                state["failure_time"] = datetime.now().isoformat()

                # Add failure entry to timeline
                timeline_entry = {
                    "type": "failure",
                    "agent": failed_agent,
                    "timestamp": state["failure_time"],
                    "description": f"Agent failure: {failed_agent}",
                }
                if "execution_timeline" not in state:
                    state["execution_timeline"] = []
                state["execution_timeline"].append(timeline_entry)

                # Identify recovery options
                recovery_options = self._identify_recovery_options(state, failed_agent)
                state["recovery_options"] = recovery_options

                # Persist interrupted state
                self.persist_state(workflow_id, state)

                return {
                    "recovery_state": state,
                    "options": recovery_options,
                    "can_resume": len(recovery_options) > 0,
                }

            except Exception as e:
                self.logger.error(
                    f"Failed to recover from agent failure for {workflow_id}: {e}"
                )
                return None

    def _identify_recovery_options(
        self, state: Dict[str, Any], failed_agent: str
    ) -> List[Dict[str, Any]]:
        """
        Identify possible recovery options after agent failure.

        Args:
            state: Workflow state
            failed_agent: Failed agent identifier

        Returns:
            List[Dict[str, Any]]: List of recovery options
        """
        options = []

        try:
            handoffs = state.get("agent_handoffs", [])
            dependencies = state.get("agent_dependencies", {})

            # Option 1: Retry with same agent
            options.append(
                {
                    "id": "retry_same_agent",
                    "description": f"Retry the failed operation with {failed_agent}",
                    "difficulty": "low",
                    "risk": "medium",
                }
            )

            # Option 2: Reroute to alternative agent
            alternative_agents = self._find_alternative_agents(
                failed_agent, dependencies
            )
            if alternative_agents:
                options.append(
                    {
                        "id": "reroute_alternative",
                        "description": f"Reroute to alternative agent: {', '.join(alternative_agents)}",
                        "difficulty": "medium",
                        "risk": "low",
                        "alternatives": alternative_agents,
                    }
                )

            # Option 3: Skip failed step if possible
            if self._can_skip_step(state, failed_agent):
                options.append(
                    {
                        "id": "skip_step",
                        "description": "Skip the failed step and continue workflow",
                        "difficulty": "high",
                        "risk": "high",
                    }
                )

            # Option 4: Rollback to previous checkpoint
            if self._has_previous_checkpoint(state):
                options.append(
                    {
                        "id": "rollback_checkpoint",
                        "description": "Rollback to last successful checkpoint",
                        "difficulty": "medium",
                        "risk": "medium",
                    }
                )

        except Exception as e:
            self.logger.error(f"Error identifying recovery options: {e}")

        return options

    def _find_alternative_agents(
        self, failed_agent: str, dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """
        Find alternative agents that can take over for failed agent.

        Args:
            failed_agent: Failed agent identifier
            dependencies: Agent dependency mapping

        Returns:
            List[str]: Alternative agent identifiers
        """
        alternatives = []

        # Simple heuristic: agents that have handed off to the failed agent
        # might be able to handle similar work
        for from_agent, targets in dependencies.items():
            if failed_agent in targets:
                alternatives.append(from_agent)

        # Add some common BMAD agent alternatives based on role similarity
        agent_alternatives = {
            "dev": ["architect", "qa"],
            "architect": ["dev", "analyst"],
            "qa": ["dev", "architect"],
            "analyst": ["architect", "pm"],
            "pm": ["analyst", "po"],
            "po": ["pm", "sm"],
            "sm": ["po", "pm"],
        }

        if failed_agent in agent_alternatives:
            alternatives.extend(agent_alternatives[failed_agent])

        return list(set(alternatives))  # Remove duplicates

    def _can_skip_step(self, state: Dict[str, Any], failed_agent: str) -> bool:
        """
        Determine if a failed step can be safely skipped.

        Args:
            state: Workflow state
            failed_agent: Failed agent identifier

        Returns:
            bool: True if step can be skipped
        """
        try:
            # Check if failed agent was optional or in parallel execution
            current_step = state.get("current_step", "")
            steps_completed = state.get("steps_completed", [])

            # If step is not critical to workflow completion, it might be skippable
            # This is a simplified check - in practice, this would need domain knowledge
            critical_agents = [
                "dev",
                "qa",
            ]  # Agents whose failure typically blocks progress
            return failed_agent not in critical_agents

        except Exception:
            return False

    def _has_previous_checkpoint(self, state: Dict[str, Any]) -> bool:
        """
        Check if workflow has a previous checkpoint for rollback.

        Args:
            state: Workflow state

        Returns:
            bool: True if checkpoint available
        """
        try:
            steps_completed = state.get("steps_completed", [])
            return len(steps_completed) > 0

        except Exception:
            return False

    def validate_state_integrity(self, workflow_id: str) -> Dict[str, Any]:
        """
        Perform comprehensive state integrity validation.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dict[str, Any]: Validation results
        """
        validation_result = {
            "workflow_id": workflow_id,
            "is_valid": True,  # assume valid unless structural/blocking issues found
            "issues": [],
            "recommendations": [],
        }

        try:
            # Load raw state file without auto-recovery to accurately assess integrity
            state_file = self.storage_dir / f"{workflow_id}.json"
            if not state_file.exists():
                validation_result["issues"].append("State file not found or unreadable")
                validation_result["recommendations"].append(
                    "Check workflow storage directory"
                )
                validation_result["is_valid"] = False
                return validation_result

            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception as e:
                validation_result["issues"].append(f"State file unreadable: {e}")
                validation_result["is_valid"] = False
                return validation_result

            # Structure validation
            if not self._validate_state_structure(state):
                validation_result["issues"].append("Invalid state structure")
                validation_result["recommendations"].append("Review state file format")
                validation_result["is_valid"] = False

            # Data consistency checks
            if state.get("status") == "completed" and not state.get("steps_completed"):
                validation_result["issues"].append(
                    "Completed workflow has no completed steps"
                )
                validation_result["recommendations"].append(
                    "Verify workflow completion logic"
                )

            # Agent dependency validation
            handoffs = state.get("agent_handoffs", [])
            dependencies = state.get("agent_dependencies", {})

            for handoff in handoffs:
                from_agent = handoff.get("from_agent")
                to_agent = handoff.get("to_agent")

                if from_agent and to_agent:
                    if from_agent not in dependencies:
                        validation_result["issues"].append(
                            f"Missing dependency record for {from_agent}"
                        )
                    elif to_agent not in dependencies[from_agent]:
                        validation_result["issues"].append(
                            f"Inconsistent dependency: {from_agent} -> {to_agent}"
                        )

            # Keep is_valid as-is (True unless structural errors set it to False)

        except Exception as e:
            validation_result["issues"].append(f"Validation error: {str(e)}")

        return validation_result

    # Metrics storage methods for monitoring and analytics

    def store_workflow_metrics(
        self,
        workflow_id: str,
        metrics_data: Dict[str, Any],
        persist_to_disk: bool = True,
    ) -> bool:
        """
        Store workflow performance metrics for monitoring and analytics.

        Args:
            workflow_id: Unique workflow identifier
            metrics_data: Metrics data to store
            persist_to_disk: Whether to persist to disk

        Returns:
            bool: True if storage successful, False otherwise
        """
        try:
            with self._lock:
                # Store in memory
                self.metrics_storage[workflow_id] = {
                    **metrics_data,
                    "stored_at": datetime.now().isoformat(),
                    "workflow_id": workflow_id,
                }

                # Update performance history
                if workflow_id not in self.performance_history:
                    self.performance_history[workflow_id] = []

                # Extract key performance metrics
                perf_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "duration": metrics_data.get("duration"),
                    "success_rate": metrics_data.get("task_success_rate", 0),
                    "efficiency_score": metrics_data.get("efficiency_score", 0),
                    "bottleneck_count": len(metrics_data.get("bottlenecks", [])),
                }

                self.performance_history[workflow_id].append(perf_entry)

                # Apply retention policies to prevent unbounded growth
                max_entries = self.retention_policies["max_entries_per_workflow"]
                if len(self.performance_history[workflow_id]) > max_entries:
                    # Keep most recent entries, compress older ones
                    recent_entries = self.performance_history[workflow_id][
                        -max_entries:
                    ]
                    self.performance_history[workflow_id] = recent_entries

                # Check if automatic cleanup is due
                if self.cleanup_enabled and self._should_run_cleanup():
                    self._run_automatic_cleanup()

                # Persist to disk if requested
                if persist_to_disk:
                    return self._persist_metrics_to_disk(workflow_id, metrics_data)
                else:
                    self.logger.debug(
                        f"Stored metrics for workflow {workflow_id} (in-memory only)"
                    )
                    return True

        except Exception as e:
            self.logger.error(
                f"Failed to store metrics for workflow {workflow_id}: {e}"
            )
            return False

    def _persist_metrics_to_disk(
        self, workflow_id: str, metrics_data: Dict[str, Any]
    ) -> bool:
        """Persist metrics data to disk storage."""
        try:
            metrics_file = self.storage_dir / f"{workflow_id}_metrics.json"
            enriched_metrics = {
                **metrics_data,
                "_metadata": {
                    "workflow_id": workflow_id,
                    "stored_at": datetime.now().isoformat(),
                    "version": "1.0",
                },
            }

            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(
                    enriched_metrics, f, indent=2, ensure_ascii=False, default=str
                )

            self.logger.debug(f"Persisted metrics to disk: {metrics_file}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to persist metrics to disk for {workflow_id}: {e}"
            )
            return False

    def retrieve_workflow_metrics(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored workflow metrics.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dictionary with metrics data or None if not found
        """
        try:
            # First try in-memory storage
            if workflow_id in self.metrics_storage:
                return self.metrics_storage[workflow_id]

            # Try disk storage
            metrics_file = self.storage_dir / f"{workflow_id}_metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r", encoding="utf-8") as f:
                    metrics_data = json.load(f)

                # Store in memory for faster future access
                self.metrics_storage[workflow_id] = metrics_data
                return metrics_data

            return None

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve metrics for workflow {workflow_id}: {e}"
            )
            return None

    def get_workflow_performance_history(
        self, workflow_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get performance history for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of performance history entries
        """
        try:
            history = self.performance_history.get(workflow_id, [])

            # If no in-memory history, try to reconstruct from stored metrics
            if not history:
                metrics = self.retrieve_workflow_metrics(workflow_id)
                if metrics:
                    # Create a single history entry from stored metrics
                    history = [
                        {
                            "timestamp": metrics.get(
                                "timestamp", datetime.now().isoformat()
                            ),
                            "duration": metrics.get("duration"),
                            "success_rate": metrics.get("task_success_rate", 0),
                            "efficiency_score": metrics.get("efficiency_score", 0),
                            "bottleneck_count": len(metrics.get("bottlenecks", [])),
                        }
                    ]

            return history

        except Exception as e:
            self.logger.error(
                f"Failed to get performance history for {workflow_id}: {e}"
            )
            return []

    def get_aggregated_metrics(
        self,
        workflow_ids: Optional[List[str]] = None,
        time_range_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics across multiple workflows.

        Args:
            workflow_ids: Optional list of workflow IDs to aggregate
            time_range_hours: Optional time range filter in hours

        Returns:
            Dictionary with aggregated metrics
        """
        try:
            if workflow_ids is None:
                workflow_ids = list(self.performance_history.keys())

            all_metrics = []
            cutoff_time = None

            if time_range_hours:
                cutoff_time = datetime.now().timestamp() - (time_range_hours * 3600)

            for workflow_id in workflow_ids:
                history = self.get_workflow_performance_history(workflow_id)

                for entry in history:
                    if cutoff_time:
                        try:
                            entry_time = datetime.fromisoformat(
                                entry["timestamp"]
                            ).timestamp()
                            if entry_time < cutoff_time:
                                continue
                        except (ValueError, KeyError):
                            continue

                    all_metrics.append(entry)

            if not all_metrics:
                return {"no_data": True}

            # Calculate aggregations
            durations = [m["duration"] for m in all_metrics if m.get("duration")]
            success_rates = [
                m["success_rate"] for m in all_metrics if m.get("success_rate")
            ]
            efficiency_scores = [
                m["efficiency_score"] for m in all_metrics if m.get("efficiency_score")
            ]
            bottleneck_counts = [
                m["bottleneck_count"]
                for m in all_metrics
                if m.get("bottleneck_count") is not None
            ]

            aggregated = {
                "total_workflows": len(workflow_ids),
                "total_measurements": len(all_metrics),
                "time_range_hours": time_range_hours,
            }

            if durations:
                aggregated.update(
                    {
                        "average_duration": sum(durations) / len(durations),
                        "min_duration": min(durations),
                        "max_duration": max(durations),
                    }
                )

            if success_rates:
                aggregated["average_success_rate"] = sum(success_rates) / len(
                    success_rates
                )

            if efficiency_scores:
                aggregated["average_efficiency_score"] = sum(efficiency_scores) / len(
                    efficiency_scores
                )

            if bottleneck_counts:
                aggregated["total_bottlenecks"] = sum(bottleneck_counts)
                aggregated["average_bottlenecks_per_workflow"] = sum(
                    bottleneck_counts
                ) / len(bottleneck_counts)

            return aggregated

        except Exception as e:
            self.logger.error(f"Failed to get aggregated metrics: {e}")
            return {"error": str(e)}

    def _should_run_cleanup(self) -> bool:
        """Check if automatic cleanup should be run based on schedule."""
        if not self.cleanup_enabled:
            return False

        time_since_last_cleanup = datetime.now() - self.last_cleanup
        cleanup_interval_hours = self.retention_policies["auto_cleanup_interval_hours"]

        return time_since_last_cleanup.total_seconds() >= (
            cleanup_interval_hours * 3600
        )

    def _run_automatic_cleanup(self) -> None:
        """Run automatic cleanup based on retention policies."""
        try:
            self.logger.info("Running automatic metrics cleanup")

            # Run cleanup with configured policies
            max_age_days = self.retention_policies["max_age_days"]
            cleaned_count = self.cleanup_old_metrics(max_age_days)

            # Check storage usage and compress if needed
            storage_usage = self._get_storage_usage_mb()
            storage_limit = self.retention_policies["storage_limit_mb"]

            if storage_usage > storage_limit:
                self.logger.warning(
                    f"Storage usage ({storage_usage:.1f}MB) exceeds limit ({storage_limit}MB)"
                )
                additional_cleaned = self._compress_old_metrics()
                cleaned_count += additional_cleaned

            self.last_cleanup = datetime.now()
            self.logger.info(
                f"Automatic cleanup completed: {cleaned_count} entries processed"
            )

        except Exception as e:
            self.logger.error(f"Automatic cleanup failed: {e}")

    def _get_storage_usage_mb(self) -> float:
        """Get current storage usage in MB."""
        try:
            if not self.storage_dir.exists():
                return 0.0

            total_size = 0
            for metrics_file in self.storage_dir.glob("*_metrics.json"):
                try:
                    total_size += metrics_file.stat().st_size
                except OSError:
                    continue

            return total_size / (1024 * 1024)  # Convert to MB

        except Exception as e:
            self.logger.error(f"Failed to get storage usage: {e}")
            return 0.0

    def _compress_old_metrics(self) -> int:
        """Compress old metrics data to reduce storage usage."""
        try:
            compression_threshold_days = self.retention_policies[
                "compression_threshold_days"
            ]
            cutoff_time = datetime.now().timestamp() - (
                compression_threshold_days * 24 * 3600
            )

            compressed_count = 0

            for workflow_id, history in self.performance_history.items():
                if len(history) > 10:  # Only compress if we have enough data
                    # Keep recent entries uncompressed, compress older ones
                    compressed_history = []
                    for entry in history:
                        try:
                            entry_time = datetime.fromisoformat(
                                entry["timestamp"]
                            ).timestamp()

                            if entry_time < cutoff_time:
                                # Compress by keeping only essential fields
                                compressed_entry = {
                                    "timestamp": entry["timestamp"],
                                    "duration": entry.get("duration"),
                                    "success_rate": entry.get("success_rate"),
                                    "efficiency_score": entry.get("efficiency_score"),
                                    # Remove detailed bottleneck info to save space
                                }
                                compressed_history.append(compressed_entry)
                                compressed_count += 1
                            else:
                                compressed_history.append(entry)

                        except (ValueError, KeyError):
                            compressed_history.append(entry)

                    self.performance_history[workflow_id] = compressed_history

            self.logger.info(f"Compressed {compressed_count} old metrics entries")
            return compressed_count

        except Exception as e:
            self.logger.error(f"Failed to compress old metrics: {e}")
            return 0

    def configure_retention_policies(self, policies: Dict[str, Any]) -> bool:
        """
        Configure retention policies for metrics storage.

        Args:
            policies: Dictionary with retention policy settings

        Returns:
            bool: True if configuration successful
        """
        try:
            # Validate policy values
            if "max_age_days" in policies and policies["max_age_days"] <= 0:
                raise ValueError("max_age_days must be positive")
            if (
                "max_entries_per_workflow" in policies
                and policies["max_entries_per_workflow"] <= 0
            ):
                raise ValueError("max_entries_per_workflow must be positive")
            if "storage_limit_mb" in policies and policies["storage_limit_mb"] <= 0:
                raise ValueError("storage_limit_mb must be positive")

            # Update policies
            self.retention_policies.update(policies)
            self.logger.info(f"Updated retention policies: {policies}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to configure retention policies: {e}")
            return False

    def get_storage_status(self) -> Dict[str, Any]:
        """
        Get detailed storage status and retention policy information.

        Returns:
            Dictionary with storage status information
        """
        try:
            storage_usage_mb = self._get_storage_usage_mb()
            total_workflows = len(self.performance_history)
            total_entries = sum(
                len(history) for history in self.performance_history.values()
            )

            # Calculate storage efficiency
            storage_limit = self.retention_policies["storage_limit_mb"]
            usage_percentage = (
                (storage_usage_mb / storage_limit * 100) if storage_limit > 0 else 0
            )

            # Estimate cleanup impact
            old_entries = 0
            cutoff_time = datetime.now().timestamp() - (
                self.retention_policies["max_age_days"] * 24 * 3600
            )

            for history in self.performance_history.values():
                for entry in history:
                    try:
                        entry_time = datetime.fromisoformat(
                            entry["timestamp"]
                        ).timestamp()
                        if entry_time < cutoff_time:
                            old_entries += 1
                    except (ValueError, KeyError):
                        continue

            return {
                "storage_usage_mb": round(storage_usage_mb, 2),
                "storage_limit_mb": storage_limit,
                "usage_percentage": round(usage_percentage, 1),
                "total_workflows": total_workflows,
                "total_entries": total_entries,
                "old_entries_count": old_entries,
                "retention_policies": self.retention_policies.copy(),
                "last_cleanup": (
                    self.last_cleanup.isoformat() if self.last_cleanup else None
                ),
                "cleanup_enabled": self.cleanup_enabled,
            }

        except Exception as e:
            self.logger.error(f"Failed to get storage status: {e}")
            return {"error": str(e)}

    def cleanup_old_metrics(self, max_age_days: int = 30) -> int:
        """
        Clean up old metrics data to prevent unbounded storage growth.

        Args:
            max_age_days: Maximum age of metrics to keep (in days)

        Returns:
            Number of metrics entries cleaned up
        """
        try:
            with self._lock:
                cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
                cleaned_count = 0

                # Clean up in-memory storage
                workflows_to_remove = []
                for workflow_id, history in self.performance_history.items():
                    # Keep only recent entries
                    recent_history = []
                    for entry in history:
                        try:
                            entry_time = datetime.fromisoformat(
                                entry["timestamp"]
                            ).timestamp()
                            if entry_time > cutoff_time:
                                recent_history.append(entry)
                            else:
                                cleaned_count += 1
                        except (ValueError, KeyError):
                            continue

                    if recent_history:
                        self.performance_history[workflow_id] = recent_history
                    else:
                        workflows_to_remove.append(workflow_id)

                # Remove workflows with no recent history
                for workflow_id in workflows_to_remove:
                    del self.performance_history[workflow_id]

                # Clean up disk files
                if self.storage_dir.exists():
                    for metrics_file in self.storage_dir.glob("*_metrics.json"):
                        try:
                            file_age = (
                                datetime.now().timestamp()
                                - metrics_file.stat().st_mtime
                            )
                            if file_age > (max_age_days * 24 * 3600):
                                metrics_file.unlink()
                                cleaned_count += 1
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to clean up metrics file {metrics_file}: {e}"
                            )

                self.logger.info(f"Cleaned up {cleaned_count} old metrics entries")
                return cleaned_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup old metrics: {e}")
            return 0
