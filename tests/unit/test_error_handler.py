"""
Unit tests for Error Handler

Tests P0 scenarios for error categorization, recovery strategies,
and error record management.
"""

from unittest.mock import Mock, patch

import pytest

from src.bmad_crewai.error_handler import (
    BmadErrorHandler,
    CircuitBreakerStrategy,
    ErrorCategory,
    ErrorRecord,
    ErrorSeverity,
    FallbackStrategy,
    RetryStrategy,
)


class TestErrorRecord:
    """Test suite for ErrorRecord."""

    def test_initialization(self):
        """Test ErrorRecord initialization."""
        # Arrange
        error = ValueError("Test error")
        context = {"operation": "test"}

        # Act
        record = ErrorRecord(
            "test-error-1",
            error,
            ErrorCategory.VALIDATION,
            ErrorSeverity.MEDIUM,
            context,
        )

        # Assert
        assert record.error_id == "test-error-1"
        assert record.error == error
        assert record.category == ErrorCategory.VALIDATION
        assert record.severity == ErrorSeverity.MEDIUM
        assert record.context == context
        assert record.resolved is False
        assert record.resolved_at is None
        assert record.recovery_attempts == []

    def test_add_recovery_attempt_success(self):
        """Test adding successful recovery attempt."""
        # Arrange
        record = ErrorRecord(
            "test-error",
            ValueError("test"),
            ErrorCategory.NETWORK,
            ErrorSeverity.MEDIUM,
        )
        strategy = "retry"

        # Act
        record.add_recovery_attempt(strategy, True, "recovery_result", "Success notes")

        # Assert
        assert len(record.recovery_attempts) == 1
        attempt = record.recovery_attempts[0]
        assert attempt["strategy"] == strategy
        assert attempt["success"] is True
        assert attempt["result"] == "recovery_result"
        assert attempt["notes"] == "Success notes"
        assert record.resolved is True
        assert record.resolved_at is not None

    def test_add_recovery_attempt_failure(self):
        """Test adding failed recovery attempt."""
        # Arrange
        record = ErrorRecord(
            "test-error",
            ValueError("test"),
            ErrorCategory.NETWORK,
            ErrorSeverity.MEDIUM,
        )

        # Act
        record.add_recovery_attempt("retry", False, None, "Failed to recover")

        # Assert
        assert len(record.recovery_attempts) == 1
        attempt = record.recovery_attempts[0]
        assert attempt["success"] is False
        assert record.resolved is False
        assert record.resolved_at is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        # Arrange
        error = ValueError("Test error")
        context = {"operation": "test"}
        record = ErrorRecord(
            "test-error", error, ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM, context
        )

        # Act
        result = record.to_dict()

        # Assert
        assert result["error_id"] == "test-error"
        assert result["error_type"] == "ValueError"
        assert result["error_message"] == "Test error"
        assert result["category"] == "validation"
        assert result["severity"] == "medium"
        assert result["context"] == context
        assert result["resolved"] is False


class TestBmadErrorHandler:
    """Test suite for BmadErrorHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = BmadErrorHandler()

    def test_initialization(self):
        """Test error handler initialization."""
        # Assert
        assert len(self.handler.recovery_strategies) == 3  # Default strategies
        assert self.handler.error_records == {}

    def test_handle_error_with_categorization(self):
        """Test error handling with automatic categorization."""
        # Arrange
        error = ValueError("Test validation error")
        context = {"operation": "validate_input"}

        # Act
        result = self.handler.handle_error(error, context, "test_operation")

        # Assert
        assert result["error_handled"] is True
        assert result["category"] == "validation"
        assert result["severity"] == "low"  # Default for validation
        assert "error_id" in result
        assert result["original_error"] == "Test validation error"

    def test_handle_error_network_error(self):
        """Test error handling for network-related errors."""
        # Arrange
        error = ConnectionError("Connection timeout")
        context = {"operation": "api_call"}

        # Act
        result = self.handler.handle_error(error, context, "network_operation")

        # Assert
        assert result["category"] == "network"
        assert result["severity"] == "medium"  # Network errors are medium

    def test_handle_error_critical_error(self):
        """Test error handling for critical authentication errors."""
        # Arrange
        error = PermissionError("Authentication failed")
        context = {"operation": "login"}

        # Act
        result = self.handler.handle_error(error, context, "auth_operation")

        # Assert
        assert result["category"] == "authentication"
        assert result["severity"] == "critical"

    def test_categorize_error_network(self):
        """Test error categorization for network errors."""
        # Arrange
        error = ConnectionError("Network is unreachable")

        # Act
        category = self.handler._categorize_error(error)

        # Assert
        assert category == ErrorCategory.NETWORK

    def test_categorize_error_configuration(self):
        """Test error categorization for configuration errors."""
        # Arrange
        error = ValueError("Missing configuration parameter")

        # Act
        category = self.handler._categorize_error(error)

        # Assert
        assert category == ErrorCategory.CONFIGURATION

    def test_categorize_error_unknown(self):
        """Test error categorization for unknown errors."""
        # Arrange
        error = RuntimeError("Unexpected error occurred")

        # Act
        category = self.handler._categorize_error(error)

        # Assert
        assert category == ErrorCategory.UNKNOWN

    def test_assess_severity_low(self):
        """Test severity assessment for low-risk errors."""
        # Arrange
        error = ValueError("Invalid input")
        context = {}

        # Act
        severity = self.handler._assess_severity(
            error, ErrorCategory.VALIDATION, context
        )

        # Assert
        assert severity == ErrorSeverity.LOW

    def test_assess_severity_medium(self):
        """Test severity assessment for medium-risk errors."""
        # Arrange
        error = ConnectionError("Connection failed")
        context = {}

        # Act
        severity = self.handler._assess_severity(error, ErrorCategory.NETWORK, context)

        # Assert
        assert severity == ErrorSeverity.MEDIUM

    def test_assess_severity_high(self):
        """Test severity assessment for high-risk errors."""
        # Arrange
        error = MemoryError("Out of memory")
        context = {}

        # Act
        severity = self.handler._assess_severity(error, ErrorCategory.RESOURCE, context)

        # Assert
        assert severity == ErrorSeverity.HIGH

    def test_assess_severity_critical(self):
        """Test severity assessment for critical errors."""
        # Arrange
        error = PermissionError("Access denied")
        context = {}

        # Act
        severity = self.handler._assess_severity(
            error, ErrorCategory.AUTHENTICATION, context
        )

        # Assert
        assert severity == ErrorSeverity.CRITICAL

    def test_get_error_summary_empty(self):
        """Test error summary when no errors have been handled."""
        # Act
        summary = self.handler.get_error_summary()

        # Assert
        assert summary["total_errors"] == 0
        assert summary["resolved_errors"] == 0
        assert summary["resolution_rate"] == 0

    def test_get_error_summary_with_errors(self):
        """Test error summary with handled errors."""
        # Arrange
        error1 = ValueError("Error 1")
        error2 = ConnectionError("Error 2")

        self.handler.handle_error(error1, {}, "op1")
        self.handler.handle_error(error2, {}, "op2")

        # Act
        summary = self.handler.get_error_summary()

        # Assert
        assert summary["total_errors"] == 2
        assert summary["resolved_errors"] == 0  # No recovery attempted
        assert summary["resolution_rate"] == 0
        assert summary["categories"]["validation"] == 1
        assert summary["categories"]["network"] == 1

    def test_get_error_details_existing(self):
        """Test getting details of existing error."""
        # Arrange
        error = ValueError("Test error")
        result = self.handler.handle_error(error, {}, "test_op")

        # Act
        details = self.handler.get_error_details(result["error_id"])

        # Assert
        assert details is not None
        assert details["error_id"] == result["error_id"]
        assert details["error_message"] == "Test error"

    def test_get_error_details_nonexistent(self):
        """Test getting details of non-existent error."""
        # Act
        details = self.handler.get_error_details("nonexistent-id")

        # Assert
        assert details is None

    def test_clear_resolved_errors(self):
        """Test clearing resolved errors older than specified days."""
        # Arrange - Mock resolved error
        error = ValueError("Test error")
        result = self.handler.handle_error(error, {}, "test_op")

        # Manually mark as resolved (normally done by recovery)
        error_record = list(self.handler.error_records.values())[0]
        error_record.resolved = True
        from datetime import datetime, timedelta

        error_record.resolved_at = datetime.now() - timedelta(
            days=40
        )  # Older than 30 days

        # Act
        cleared_count = self.handler.clear_resolved_errors(older_than_days=30)

        # Assert
        assert cleared_count == 1
        assert len(self.handler.error_records) == 0

    def test_add_recovery_strategy(self):
        """Test adding custom recovery strategy."""
        # Arrange
        strategy = Mock()
        strategy.name = "custom_strategy"

        # Act
        self.handler.add_recovery_strategy(strategy)

        # Assert
        assert len(self.handler.recovery_strategies) == 4  # 3 default + 1 custom
        assert strategy in self.handler.recovery_strategies


class TestRetryStrategy:
    """Test suite for RetryStrategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = RetryStrategy(max_retries=2)

    def test_initialization(self):
        """Test retry strategy initialization."""
        # Assert
        assert self.strategy.max_retries == 2
        assert self.strategy.base_delay == 1.0
        assert self.strategy.max_delay == 60.0

    @patch("time.sleep")
    def test_execute_success_on_first_try(self, mock_sleep):
        """Test successful execution on first try."""
        # Arrange
        operation = Mock(return_value="success")

        # Act
        result = self.strategy.execute(ValueError("test"), {"operation": operation})

        # Assert
        assert result["success"] is True
        assert result["result"] == "success"
        assert result["attempts"] == 1
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_execute_success_after_retry(self, mock_sleep):
        """Test successful execution after retry."""
        # Arrange
        operation = Mock(side_effect=[ValueError("fail"), "success"])

        # Act
        result = self.strategy.execute(ValueError("test"), {"operation": operation})

        # Assert
        assert result["success"] is True
        assert result["result"] == "success"
        assert result["attempts"] == 2
        assert mock_sleep.call_count == 1

    @patch("time.sleep")
    def test_execute_failure_after_max_retries(self, mock_sleep):
        """Test failure after maximum retries."""
        # Arrange
        operation = Mock(side_effect=ValueError("persistent failure"))

        # Act
        result = self.strategy.execute(ValueError("test"), {"operation": operation})

        # Assert
        assert result["success"] is False
        assert "attempts" in result
        assert mock_sleep.call_count == 1  # Only 1 sleep for 2 retries

    def test_can_handle_network_error(self):
        """Test that retry strategy can handle network errors."""
        # Act & Assert
        assert (
            self.strategy.can_handle(ConnectionError("test"), ErrorCategory.NETWORK)
            is True
        )
        assert (
            self.strategy.can_handle(TimeoutError("test"), ErrorCategory.TIMEOUT)
            is True
        )
        assert (
            self.strategy.can_handle(ValueError("test"), ErrorCategory.VALIDATION)
            is False
        )


class TestFallbackStrategy:
    """Test suite for FallbackStrategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.fallback_operation = Mock(return_value="fallback_result")
        self.strategy = FallbackStrategy(self.fallback_operation)

    def test_execute_success(self):
        """Test successful fallback execution."""
        # Act
        result = self.strategy.execute(ValueError("test"), {})

        # Assert
        assert result["success"] is True
        assert result["result"] == "fallback_result"
        self.fallback_operation.assert_called_once()

    def test_execute_failure(self):
        """Test fallback execution failure."""
        # Arrange
        self.fallback_operation.side_effect = Exception("Fallback failed")

        # Act
        result = self.strategy.execute(ValueError("test"), {})

        # Assert
        assert result["success"] is False
        assert "error" in result

    def test_can_handle_most_errors(self):
        """Test that fallback can handle most error types."""
        # Act & Assert
        assert (
            self.strategy.can_handle(ValueError("test"), ErrorCategory.VALIDATION)
            is True
        )
        assert (
            self.strategy.can_handle(ConnectionError("test"), ErrorCategory.NETWORK)
            is True
        )
        assert (
            self.strategy.can_handle(PermissionError("test"), ErrorCategory.CRITICAL)
            is False
        )


class TestCircuitBreakerStrategy:
    """Test suite for CircuitBreakerStrategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = CircuitBreakerStrategy(failure_threshold=2, reset_timeout=30)

    def test_initialization(self):
        """Test circuit breaker initialization."""
        # Assert
        assert self.strategy.failure_threshold == 2
        assert self.strategy.reset_timeout == 30
        assert self.strategy.failure_count == 0
        assert self.strategy.state == "closed"

    @patch("src.bmad_crewai.error_handler.datetime")
    def test_execute_under_threshold(self, mock_datetime):
        """Test execution when failure count is under threshold."""
        # Arrange
        mock_datetime.now.return_value = Mock()

        # Act
        result = self.strategy.execute(ValueError("test"), {})

        # Assert
        assert result["success"] is False
        assert self.strategy.failure_count == 1
        assert self.strategy.state == "closed"

    @patch("src.bmad_crewai.error_handler.datetime")
    def test_execute_at_threshold_opens_circuit(self, mock_datetime):
        """Test that circuit opens when failure threshold is reached."""
        # Arrange
        mock_datetime.now.return_value = Mock()

        # Act - Two failures to reach threshold
        self.strategy.execute(ValueError("test1"), {})
        result = self.strategy.execute(ValueError("test2"), {})

        # Assert
        assert result["success"] is False
        assert self.strategy.failure_count == 2
        assert self.strategy.state == "open"
        assert "Circuit breaker opened" in result["error"]

    def test_can_handle_resource_errors(self):
        """Test that circuit breaker can handle resource errors."""
        # Act & Assert
        assert (
            self.strategy.can_handle(MemoryError("test"), ErrorCategory.RESOURCE)
            is True
        )
        assert (
            self.strategy.can_handle(ConnectionError("test"), ErrorCategory.NETWORK)
            is True
        )
        assert (
            self.strategy.can_handle(ValueError("test"), ErrorCategory.VALIDATION)
            is False
        )
