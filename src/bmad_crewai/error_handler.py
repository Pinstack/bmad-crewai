"""
Error Handler for BMAD CrewAI Integration

This module provides comprehensive error handling and recovery mechanisms
for CrewAI operations and BMAD agent interactions.
"""

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .exceptions import BmadCrewAIError


class ErrorSeverity(Enum):
    """Enumeration of error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Enumeration of error categories."""

    NETWORK = "network"
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    AGENT = "agent"
    WORKFLOW = "workflow"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ErrorRecord:
    """
    Container for error information and recovery attempts.

    This class tracks individual errors, their context, and recovery attempts.
    """

    def __init__(
        self,
        error_id: str,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.error_id = error_id
        self.error = error
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.now()
        self.recovery_attempts: List[Dict[str, Any]] = []
        self.resolved = False
        self.resolved_at: Optional[datetime] = None
        self.resolution_notes: Optional[str] = None

    def add_recovery_attempt(
        self,
        strategy: str,
        success: bool,
        result: Optional[Any] = None,
        notes: Optional[str] = None,
    ):
        """
        Add a recovery attempt record.

        Args:
            strategy: Recovery strategy used
            success: Whether the recovery was successful
            result: Result of the recovery attempt
            notes: Additional notes about the attempt
        """
        attempt = {
            "timestamp": datetime.now(),
            "strategy": strategy,
            "success": success,
            "result": result,
            "notes": notes,
        }
        self.recovery_attempts.append(attempt)

        if success:
            self.resolved = True
            self.resolved_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error record to dictionary representation."""
        return {
            "error_id": self.error_id,
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "recovery_attempts": [
                {
                    "timestamp": attempt["timestamp"].isoformat(),
                    "strategy": attempt["strategy"],
                    "success": attempt["success"],
                    "result": attempt["result"],
                    "notes": attempt["notes"],
                }
                for attempt in self.recovery_attempts
            ],
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
        }


class RecoveryStrategy:
    """
    Base class for error recovery strategies.

    Subclasses should implement the execute method to define specific
    recovery behaviors for different types of errors.
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def execute(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the recovery strategy.

        Args:
            error: The exception that occurred
            context: Context information about the error

        Returns:
            Dictionary with recovery result information
        """
        raise NotImplementedError("Subclasses must implement execute method")

    def can_handle(self, error: Exception, category: ErrorCategory) -> bool:
        """
        Check if this strategy can handle the given error.

        Args:
            error: The exception that occurred
            category: Error category

        Returns:
            bool: True if this strategy can handle the error
        """
        return False


class RetryStrategy(RecoveryStrategy):
    """Recovery strategy that retries the operation with exponential backoff."""

    def __init__(
        self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0
    ):
        super().__init__("retry", "Retry operation with exponential backoff")
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def execute(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute retry strategy."""
        operation = context.get("operation")
        if not operation:
            return {"success": False, "error": "No operation provided for retry"}

        for attempt in range(self.max_retries):
            try:
                delay = min(self.base_delay * (2**attempt), self.max_delay)
                if attempt > 0:
                    time.sleep(delay)

                result = operation()
                return {"success": True, "result": result, "attempts": attempt + 1}

            except Exception as retry_error:
                if attempt == self.max_retries - 1:
                    return {
                        "success": False,
                        "error": str(retry_error),
                        "attempts": attempt + 1,
                    }

        return {"success": False, "error": "Max retries exceeded"}

    def can_handle(self, error: Exception, category: ErrorCategory) -> bool:
        """Check if retry strategy is appropriate."""
        # Retry for network, timeout, and resource errors
        return category in [
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RESOURCE,
        ]


class FallbackStrategy(RecoveryStrategy):
    """Recovery strategy that uses a fallback operation."""

    def __init__(self, fallback_operation: Callable):
        super().__init__("fallback", "Use fallback operation")
        self.fallback_operation = fallback_operation

    def execute(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute fallback strategy."""
        try:
            result = self.fallback_operation()
            return {"success": True, "result": result}
        except Exception as fallback_error:
            return {"success": False, "error": str(fallback_error)}

    def can_handle(self, error: Exception, category: ErrorCategory) -> bool:
        """Check if fallback strategy is appropriate."""
        # Fallback for most error types except critical ones
        return category != ErrorCategory.CRITICAL


class CircuitBreakerStrategy(RecoveryStrategy):
    """Recovery strategy that implements circuit breaker pattern."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        super().__init__("circuit_breaker", "Implement circuit breaker pattern")
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open

    def execute(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute circuit breaker strategy."""
        current_time = datetime.now()

        # Update failure count
        self.failure_count += 1
        self.last_failure_time = current_time

        # Check if circuit should open
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            return {
                "success": False,
                "error": "Circuit breaker opened due to repeated failures",
                "state": self.state,
            }

        # If circuit is open, check if it should transition to half-open
        if self.state == "open":
            if (
                self.last_failure_time
                and (current_time - self.last_failure_time).seconds > self.reset_timeout
            ):
                self.state = "half-open"
                return {
                    "success": False,
                    "error": "Circuit breaker in half-open state",
                    "state": self.state,
                }

        return {"success": False, "error": str(error), "state": self.state}

    def can_handle(self, error: Exception, category: ErrorCategory) -> bool:
        """Check if circuit breaker is appropriate."""
        # Circuit breaker for network and resource errors
        return category in [ErrorCategory.NETWORK, ErrorCategory.RESOURCE]


class WorkflowSkipStrategy(RecoveryStrategy):
    """Recovery strategy that skips failed workflow tasks and continues."""

    def __init__(self, skip_condition: Optional[Callable] = None):
        super().__init__("workflow_skip", "Skip failed task and continue workflow")
        self.skip_condition = skip_condition

    def execute(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow skip strategy."""
        task_spec = context.get("task_spec", {})
        workflow_context = context.get("workflow_context", {})

        # Check if this task can be safely skipped
        if self.skip_condition:
            can_skip = self.skip_condition(error, context)
        else:
            # Default: skip if task is marked as optional
            can_skip = task_spec.get("optional", False)

        if can_skip:
            return {
                "success": True,
                "action": "skipped",
                "reason": "Task marked as optional or safe to skip",
                "workflow_continuation": True,
            }

        return {
            "success": False,
            "error": "Task cannot be safely skipped",
            "workflow_continuation": False,
        }

    def can_handle(self, error: Exception, category: ErrorCategory) -> bool:
        """Check if skip strategy is appropriate."""
        # Skip strategy for validation and workflow errors
        return category in [ErrorCategory.VALIDATION, ErrorCategory.WORKFLOW]


class AgentSwitchStrategy(RecoveryStrategy):
    """Recovery strategy that switches to a different agent for task execution."""

    def __init__(self, agent_registry=None):
        super().__init__("agent_switch", "Switch to different agent for task execution")
        self.agent_registry = agent_registry

    def execute(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent switch strategy."""
        current_agent = context.get("current_agent")
        task_requirements = context.get("task_requirements", {})
        workflow_id = context.get("workflow_id")

        if not self.agent_registry:
            return {
                "success": False,
                "error": "No agent registry available for agent switching",
            }

        # Find alternative agent with similar capabilities
        alternative_agent = self._find_alternative_agent(
            current_agent, task_requirements, workflow_id
        )

        if alternative_agent:
            return {
                "success": True,
                "action": "agent_switched",
                "new_agent": alternative_agent,
                "reason": f"Switched from {current_agent} to {alternative_agent}",
            }

        return {
            "success": False,
            "error": "No suitable alternative agent found",
        }

    def _find_alternative_agent(
        self, current_agent: str, task_requirements: Dict[str, Any], workflow_id: str
    ) -> Optional[str]:
        """Find an alternative agent for task execution."""
        if not self.agent_registry:
            return None

        # Get all available agents except current one
        available_agents = [
            agent_id
            for agent_id in self.agent_registry.list_bmad_agents()
            if agent_id != current_agent
        ]

        # For now, return first available agent (could be enhanced with capability matching)
        return available_agents[0] if available_agents else None

    def can_handle(self, error: Exception, category: ErrorCategory) -> bool:
        """Check if agent switch is appropriate."""
        # Agent switch for agent and workflow errors
        return category in [ErrorCategory.AGENT, ErrorCategory.WORKFLOW]


class WorkflowRollbackStrategy(RecoveryStrategy):
    """Recovery strategy that rolls back workflow to previous checkpoint."""

    def __init__(self, state_manager=None):
        super().__init__(
            "workflow_rollback", "Rollback workflow to previous checkpoint"
        )
        self.state_manager = state_manager

    def execute(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow rollback strategy."""
        workflow_id = context.get("workflow_id")
        checkpoint_id = context.get("checkpoint_id")

        if not self.state_manager:
            return {
                "success": False,
                "error": "No state manager available for rollback",
            }

        # Attempt to rollback to checkpoint
        recovery_result = self.state_manager.recover_workflow_from_checkpoint(
            workflow_id, checkpoint_id
        )

        if recovery_result:
            return {
                "success": True,
                "action": "rolled_back",
                "checkpoint_id": checkpoint_id,
                "recovery_details": recovery_result,
            }

        return {
            "success": False,
            "error": "Failed to rollback to checkpoint",
        }

    def can_handle(self, error: Exception, category: ErrorCategory) -> bool:
        """Check if rollback is appropriate."""
        # Rollback for critical and workflow errors
        return category in [ErrorCategory.CRITICAL, ErrorCategory.WORKFLOW]


class BmadErrorHandler:
    """
    Comprehensive error handler for BMAD CrewAI operations.

    This class provides error detection, categorization, recovery strategies,
    and logging capabilities for robust error handling.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the error handler.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_records: Dict[str, ErrorRecord] = {}
        self.recovery_strategies: List[RecoveryStrategy] = []

        # Initialize default recovery strategies
        self._initialize_default_strategies()

    def _initialize_default_strategies(self):
        """Initialize default recovery strategies."""
        self.recovery_strategies.extend(
            [
                RetryStrategy(),
                CircuitBreakerStrategy(),
                FallbackStrategy(lambda: {"fallback": "default_response"}),
                WorkflowSkipStrategy(),
                AgentSwitchStrategy(),
                WorkflowRollbackStrategy(),
            ]
        )

        # Initialize circuit breaker registry for different operations
        self.circuit_breakers: Dict[str, CircuitBreakerStrategy] = {}

    def get_circuit_breaker(self, operation_name: str) -> CircuitBreakerStrategy:
        """
        Get or create a circuit breaker for a specific operation.

        Args:
            operation_name: Name of the operation

        Returns:
            CircuitBreakerStrategy instance for the operation
        """
        if operation_name not in self.circuit_breakers:
            # Create a new circuit breaker with default settings
            self.circuit_breakers[operation_name] = CircuitBreakerStrategy(
                failure_threshold=5,  # Allow 5 failures before opening
                reset_timeout=300,  # 5 minutes timeout
            )
            self.logger.info(f"Created circuit breaker for operation: {operation_name}")

        return self.circuit_breakers[operation_name]

    def is_circuit_open(self, operation_name: str) -> bool:
        """
        Check if the circuit breaker for an operation is open.

        Args:
            operation_name: Name of the operation

        Returns:
            bool: True if circuit is open, False otherwise
        """
        circuit_breaker = self.get_circuit_breaker(operation_name)
        return circuit_breaker.state == "open"

    def reset_circuit_breaker(self, operation_name: str) -> bool:
        """
        Manually reset a circuit breaker for an operation.

        Args:
            operation_name: Name of the operation

        Returns:
            bool: True if reset successful, False if operation not found
        """
        if operation_name in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[operation_name]
            circuit_breaker.failure_count = 0
            circuit_breaker.state = "closed"
            circuit_breaker.last_failure_time = None
            self.logger.info(
                f"Manually reset circuit breaker for operation: {operation_name}"
            )
            return True

        self.logger.warning(f"No circuit breaker found for operation: {operation_name}")
        return False

    def get_circuit_breaker_status(self, operation_name: str) -> Dict[str, Any]:
        """
        Get the status of a circuit breaker for an operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Dictionary with circuit breaker status
        """
        circuit_breaker = self.get_circuit_breaker(operation_name)
        return {
            "operation": operation_name,
            "state": circuit_breaker.state,
            "failure_count": circuit_breaker.failure_count,
            "failure_threshold": circuit_breaker.failure_threshold,
            "last_failure_time": (
                circuit_breaker.last_failure_time.isoformat()
                if circuit_breaker.last_failure_time
                else None
            ),
            "is_open": circuit_breaker.state == "open",
        }

    def handle_workflow_error(
        self,
        error: Exception,
        workflow_context: Dict[str, Any],
        agent_registry=None,
        state_manager=None,
    ) -> Dict[str, Any]:
        """
        Handle workflow-specific errors with advanced recovery strategies.

        Args:
            error: The exception that occurred
            workflow_context: Workflow execution context
            agent_registry: Optional agent registry for agent switching
            state_manager: Optional state manager for rollback operations

        Returns:
            Dict containing error handling results and recovery actions
        """
        # Categorize the error
        category = self._categorize_workflow_error(error, workflow_context)
        severity = self._assess_workflow_error_severity(error, workflow_context)

        # Create error record
        error_id = f"workflow_{workflow_context.get('workflow_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        error_record = ErrorRecord(
            error_id, error, category, severity, workflow_context
        )

        # Try workflow-specific recovery strategies first
        recovery_result = self._attempt_workflow_recovery(
            error_record, workflow_context, agent_registry, state_manager
        )

        if recovery_result.get("success"):
            error_record.add_recovery_attempt(
                recovery_result["strategy"],
                True,
                recovery_result,
                f"Workflow recovery successful: {recovery_result.get('action', 'unknown')}",
            )
        else:
            # Fall back to standard recovery strategies
            standard_recovery = self.handle_error(
                error,
                workflow_context,
                f"workflow_{workflow_context.get('workflow_id', 'unknown')}",
            )
            recovery_result = standard_recovery

        return {
            "error_handled": True,
            "recovery_attempted": True,
            "recovery_success": recovery_result.get("success", False),
            "recovery_action": recovery_result.get("action", "none"),
            "error_category": category.value,
            "error_severity": severity.value,
            "workflow_continuation_possible": recovery_result.get(
                "workflow_continuation", False
            ),
            "details": recovery_result,
        }

    def _categorize_workflow_error(
        self, error: Exception, workflow_context: Dict[str, Any]
    ) -> ErrorCategory:
        """Categorize workflow-specific errors."""
        error_message = str(error).lower()
        error_type = type(error).__name__.lower()

        # Check for workflow-specific error patterns
        if "agent" in error_message or "agent" in error_type:
            return ErrorCategory.AGENT
        elif any(
            term in error_message
            for term in ["workflow", "task", "checkpoint", "state"]
        ):
            return ErrorCategory.WORKFLOW
        elif any(term in error_message for term in ["timeout", "deadline"]):
            return ErrorCategory.TIMEOUT
        elif any(term in error_message for term in ["network", "connection", "http"]):
            return ErrorCategory.NETWORK
        elif any(
            term in error_message for term in ["validation", "invalid", "malformed"]
        ):
            return ErrorCategory.VALIDATION
        elif any(
            term in error_message for term in ["resource", "memory", "disk", "quota"]
        ):
            return ErrorCategory.RESOURCE
        elif any(
            term in error_message
            for term in ["authentication", "authorization", "permission"]
        ):
            return ErrorCategory.AUTHENTICATION
        else:
            return ErrorCategory.UNKNOWN

    def _assess_workflow_error_severity(
        self, error: Exception, workflow_context: Dict[str, Any]
    ) -> ErrorSeverity:
        """Assess the severity of workflow errors."""
        # Check if this is a critical workflow task
        task_spec = workflow_context.get("task_spec", {})
        if task_spec.get("critical", False):
            return ErrorSeverity.CRITICAL

        # Check error category for severity hints
        error_category = self._categorize_workflow_error(error, workflow_context)

        if error_category in [ErrorCategory.CRITICAL, ErrorCategory.AUTHENTICATION]:
            return ErrorSeverity.HIGH
        elif error_category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
            return ErrorSeverity.MEDIUM
        elif error_category in [ErrorCategory.VALIDATION, ErrorCategory.WORKFLOW]:
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.MEDIUM

    def _attempt_workflow_recovery(
        self,
        error_record: ErrorRecord,
        workflow_context: Dict[str, Any],
        agent_registry=None,
        state_manager=None,
    ) -> Dict[str, Any]:
        """Attempt workflow-specific recovery strategies."""
        applicable_strategies = []

        # Prioritize workflow-specific strategies
        for strategy in self.recovery_strategies:
            if isinstance(
                strategy,
                (WorkflowSkipStrategy, AgentSwitchStrategy, WorkflowRollbackStrategy),
            ):
                if strategy.can_handle(error_record.error, error_record.category):
                    applicable_strategies.append(strategy)

        # Try each applicable strategy
        for strategy in applicable_strategies:
            try:
                # Prepare strategy-specific context
                strategy_context = self._prepare_strategy_context(
                    strategy, workflow_context, agent_registry, state_manager
                )

                result = strategy.execute(error_record.error, strategy_context)

                if result.get("success"):
                    return {
                        "success": True,
                        "strategy": strategy.name,
                        "action": result.get("action"),
                        "workflow_continuation": result.get(
                            "workflow_continuation", False
                        ),
                        "details": result,
                    }

            except Exception as strategy_error:
                self.logger.warning(
                    f"Strategy {strategy.name} failed: {strategy_error}"
                )
                continue

        return {"success": False, "error": "No applicable recovery strategy succeeded"}

    def _prepare_strategy_context(
        self,
        strategy: RecoveryStrategy,
        workflow_context: Dict[str, Any],
        agent_registry=None,
        state_manager=None,
    ) -> Dict[str, Any]:
        """Prepare context specific to the recovery strategy."""
        base_context = workflow_context.copy()

        if isinstance(strategy, AgentSwitchStrategy):
            base_context["agent_registry"] = agent_registry
        elif isinstance(strategy, WorkflowRollbackStrategy):
            base_context["state_manager"] = state_manager
        elif isinstance(strategy, WorkflowSkipStrategy):
            base_context["workflow_context"] = workflow_context

        return base_context

    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        operation_name: str = "unknown_operation",
    ) -> Dict[str, Any]:
        """
        Handle an error with automatic recovery attempts.

        Args:
            error: The exception that occurred
            context: Additional context about the error
            operation_name: Name of the operation that failed

        Returns:
            Dictionary with error handling result
        """
        context = context or {}

        # Categorize and assess error
        category = self._categorize_error(error)
        severity = self._assess_severity(error, category, context)

        # Create error record
        error_id = f"{operation_name}_{int(time.time())}_{len(self.error_records)}"
        error_record = ErrorRecord(error_id, error, category, severity, context)
        self.error_records[error_id] = error_record

        # Log error
        self.logger.error(
            f"Error in {operation_name}: {error} (Category: {category.value}, Severity: {severity.value})"
        )

        # Attempt recovery
        recovery_result = self._attempt_recovery(
            error, category, context, operation_name
        )

        # Record recovery attempt
        error_record.add_recovery_attempt(
            recovery_result.get("strategy", "none"),
            recovery_result.get("success", False),
            recovery_result.get("result"),
            recovery_result.get("notes"),
        )

        # Return comprehensive result
        return {
            "error_handled": True,
            "error_id": error_id,
            "original_error": str(error),
            "category": category.value,
            "severity": severity.value,
            "recovery_attempted": True,
            "recovery_success": recovery_result.get("success", False),
            "recovery_result": recovery_result.get("result"),
            "error_record": error_record.to_dict(),
        }

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error based on its type and characteristics."""
        error_type = type(error).__name__
        error_message = str(error).lower()

        # Network-related errors
        if any(
            keyword in error_message
            for keyword in ["connection", "timeout", "network", "http", "api"]
        ):
            return ErrorCategory.NETWORK

        # Configuration errors
        if any(
            keyword in error_message
            for keyword in ["config", "setting", "parameter", "missing"]
        ):
            return ErrorCategory.CONFIGURATION

        # Authentication errors
        if any(
            keyword in error_message
            for keyword in ["auth", "credential", "permission", "unauthorized"]
        ):
            return ErrorCategory.AUTHENTICATION

        # Validation errors
        if any(
            keyword in error_message
            for keyword in ["validation", "invalid", "format", "schema"]
        ):
            return ErrorCategory.VALIDATION

        # Resource errors
        if any(
            keyword in error_message
            for keyword in ["resource", "memory", "disk", "quota"]
        ):
            return ErrorCategory.RESOURCE

        # Timeout errors
        if any(keyword in error_message for keyword in ["timeout", "deadline"]):
            return ErrorCategory.TIMEOUT

        # Agent-related errors
        if any(keyword in error_message for keyword in ["agent", "crewai", "tool"]):
            return ErrorCategory.AGENT

        # Workflow errors
        if any(keyword in error_message for keyword in ["workflow", "task", "process"]):
            return ErrorCategory.WORKFLOW

        return ErrorCategory.UNKNOWN

    def _assess_severity(
        self, error: Exception, category: ErrorCategory, context: Dict[str, Any]
    ) -> ErrorSeverity:
        """Assess the severity of an error."""
        # Critical errors
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.CRITICAL

        # High severity errors
        if category == ErrorCategory.RESOURCE:
            return ErrorSeverity.HIGH

        # Medium severity errors
        if category in [
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.AGENT,
        ]:
            return ErrorSeverity.MEDIUM

        # Context-based severity
        if context.get("impact") == "system_wide":
            return ErrorSeverity.HIGH
        elif context.get("impact") == "workflow_blocking":
            return ErrorSeverity.MEDIUM

        # Default to low severity
        return ErrorSeverity.LOW

    def _attempt_recovery(
        self,
        error: Exception,
        category: ErrorCategory,
        context: Dict[str, Any],
        operation_name: str = "unknown_operation",
    ) -> Dict[str, Any]:
        """Attempt to recover from an error using available strategies."""
        # First, check if circuit breaker is open for this operation
        if self.is_circuit_open(operation_name):
            self.logger.warning(
                f"Circuit breaker is open for operation: {operation_name}"
            )
            return {
                "success": False,
                "strategy": "circuit_breaker",
                "error": f"Circuit breaker is open for operation {operation_name}",
                "circuit_state": "open",
            }

        # Try recovery strategies
        for strategy in self.recovery_strategies:
            if strategy.can_handle(error, category):
                try:
                    self.logger.info(
                        f"Attempting recovery with strategy: {strategy.name}"
                    )
                    result = strategy.execute(error, context)

                    if result.get("success"):
                        self.logger.info(
                            f"Recovery successful with strategy: {strategy.name}"
                        )
                        result["strategy"] = strategy.name
                        return result
                    else:
                        self.logger.debug(
                            f"Recovery failed with strategy: {strategy.name}"
                        )
                        # If this is a circuit breaker strategy, update our registry
                        if isinstance(strategy, CircuitBreakerStrategy):
                            circuit_breaker = self.get_circuit_breaker(operation_name)
                            # Update the circuit breaker state based on the strategy result
                            if "state" in result:
                                circuit_breaker.state = result["state"]
                                circuit_breaker.failure_count = getattr(
                                    strategy,
                                    "failure_count",
                                    circuit_breaker.failure_count,
                                )

                except Exception as recovery_error:
                    self.logger.warning(
                        f"Recovery strategy {strategy.name} threw error: {recovery_error}"
                    )

        # No recovery strategy succeeded - this counts as a failure for circuit breaker
        circuit_breaker = self.get_circuit_breaker(operation_name)
        try:
            circuit_result = circuit_breaker.execute(error, context)
            if "state" in circuit_result and circuit_result["state"] == "open":
                self.logger.warning(
                    f"Circuit breaker opened for operation: {operation_name}"
                )
        except Exception as cb_error:
            self.logger.error(f"Circuit breaker execution failed: {cb_error}")

        return {
            "success": False,
            "strategy": "none",
            "error": "No suitable recovery strategy found or all strategies failed",
        }

    def add_recovery_strategy(self, strategy: RecoveryStrategy):
        """
        Add a custom recovery strategy.

        Args:
            strategy: Recovery strategy instance
        """
        self.recovery_strategies.append(strategy)
        self.logger.info(f"Added recovery strategy: {strategy.name}")

    def get_error_summary(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get summary of errors handled.

        Args:
            since: Optional datetime to filter errors after this time

        Returns:
            Dictionary with error summary statistics
        """
        errors = list(self.error_records.values())

        if since:
            errors = [e for e in errors if e.timestamp >= since]

        total_errors = len(errors)
        resolved_errors = sum(1 for e in errors if e.resolved)
        critical_errors = sum(1 for e in errors if e.severity == ErrorSeverity.CRITICAL)

        # Category breakdown
        categories = {}
        for error in errors:
            cat = error.category.value
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_errors": total_errors,
            "resolved_errors": resolved_errors,
            "unresolved_errors": total_errors - resolved_errors,
            "critical_errors": critical_errors,
            "resolution_rate": (
                (resolved_errors / total_errors * 100) if total_errors > 0 else 0
            ),
            "categories": categories,
        }

    def get_error_details(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific error."""
        if error_id in self.error_records:
            return self.error_records[error_id].to_dict()
        return None

    def clear_resolved_errors(self, older_than_days: int = 30) -> int:
        """
        Clear resolved errors older than specified days.

        Args:
            older_than_days: Age threshold in days

        Returns:
            Number of errors cleared
        """
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        to_remove = []

        for error_id, error_record in self.error_records.items():
            if (
                error_record.resolved
                and error_record.resolved_at
                and error_record.resolved_at < cutoff_date
            ):
                to_remove.append(error_id)

        for error_id in to_remove:
            del self.error_records[error_id]

        self.logger.info(
            f"Cleared {len(to_remove)} resolved errors older than {older_than_days} days"
        )
        return len(to_remove)
