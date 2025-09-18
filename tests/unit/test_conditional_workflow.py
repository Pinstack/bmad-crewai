"""
Unit tests for conditional workflow execution functionality.
"""

import logging
import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from src.bmad_crewai.crewai_engine import BmadWorkflowEngine
from src.bmad_crewai.exceptions import BmadCrewAIError


class TestConditionalWorkflow(unittest.TestCase):
    """Test cases for conditional workflow execution."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger(__name__)
        self.engine = BmadWorkflowEngine(logger=self.logger)

    def test_should_skip_task_context_condition_true(self):
        """Test that tasks are skipped when context conditions are met."""
        task_spec = {
            "description": "Test task",
            "condition": {
                "type": "context_check",
                "key": "skip_task",
                "operator": "equals",
                "value": True,
            },
        }
        context = {"skip_task": True}
        results = {"task_results": []}

        should_skip = self.engine._should_skip_task(task_spec, context, results)
        self.assertTrue(should_skip)

    def test_should_skip_task_context_condition_false(self):
        """Test that tasks are not skipped when context conditions are not met."""
        task_spec = {
            "description": "Test task",
            "condition": {
                "type": "context_check",
                "key": "skip_task",
                "operator": "equals",
                "value": True,
            },
        }
        context = {"skip_task": False}
        results = {"task_results": []}

        should_skip = self.engine._should_skip_task(task_spec, context, results)
        self.assertFalse(should_skip)

    def test_should_skip_task_no_condition(self):
        """Test that tasks without conditions are not skipped."""
        task_spec = {"description": "Test task"}
        context = {}
        results = {"task_results": []}

        should_skip = self.engine._should_skip_task(task_spec, context, results)
        self.assertFalse(should_skip)

    def test_evaluate_context_condition_equals(self):
        """Test context condition evaluation with equals operator."""
        condition = {"key": "status", "operator": "equals", "value": "success"}
        context = {"status": "success"}

        result = self.engine._evaluate_context_condition(condition, context)
        self.assertTrue(result)

    def test_evaluate_context_condition_not_equals(self):
        """Test context condition evaluation with not_equals operator."""
        condition = {"key": "status", "operator": "not_equals", "value": "failed"}
        context = {"status": "success"}

        result = self.engine._evaluate_context_condition(condition, context)
        self.assertTrue(result)

    def test_evaluate_context_condition_contains(self):
        """Test context condition evaluation with contains operator."""
        condition = {"key": "tags", "operator": "contains", "value": "urgent"}
        context = {"tags": ["urgent", "important"]}

        result = self.engine._evaluate_context_condition(condition, context)
        self.assertTrue(result)

    def test_evaluate_context_condition_greater_than(self):
        """Test context condition evaluation with greater_than operator."""
        condition = {"key": "priority", "operator": "greater_than", "value": 5}
        context = {"priority": 8}

        result = self.engine._evaluate_context_condition(condition, context)
        self.assertTrue(result)

    def test_evaluate_result_condition(self):
        """Test result condition evaluation."""
        condition = {"task_index": 0, "status": "success"}
        results = {"task_results": [{"status": "success", "message": "Task completed"}]}

        result = self.engine._evaluate_result_condition(condition, results)
        self.assertTrue(result)

    def test_evaluate_time_condition(self):
        """Test time-based condition evaluation."""
        current_hour = datetime.now().hour
        condition = {"start_hour": current_hour - 1, "end_hour": current_hour + 1}

        result = self.engine._evaluate_time_condition(condition)
        self.assertTrue(result)

    def test_evaluate_dependency_condition(self):
        """Test dependency condition evaluation."""
        condition = {"dependency": "database"}
        results = {"task_results": []}

        # Test with dependency available in context
        context = {"database": True}
        result = self.engine._evaluate_dependency_condition(condition, results)
        self.assertTrue(result)

        # Test with dependency not available
        context = {}
        result = self.engine._evaluate_dependency_condition(condition, results)
        self.assertFalse(result)

    def test_resolve_branch_target_by_index(self):
        """Test branching target resolution by task index."""
        result = self.engine._resolve_branch_target(2, 0, 5)
        self.assertEqual(result, 2)

    def test_resolve_branch_target_next(self):
        """Test branching target resolution for next task."""
        result = self.engine._resolve_branch_target("next", 0, 5)
        self.assertEqual(result, 1)

    def test_resolve_branch_target_end(self):
        """Test branching target resolution for workflow end."""
        result = self.engine._resolve_branch_target("end", 0, 5)
        self.assertEqual(result, 5)

    def test_resolve_branch_target_task_reference(self):
        """Test branching target resolution for task reference."""
        result = self.engine._resolve_branch_target("task_3", 0, 5)
        self.assertEqual(result, 3)

    def test_check_branching_condition_status(self):
        """Test branching condition check for status."""
        condition = {"type": "status_check", "expected_status": "success"}
        task_result = {"status": "success"}

        result = self.engine._check_branching_condition(condition, task_result)
        self.assertTrue(result)

    def test_check_branching_condition_result(self):
        """Test branching condition check for result value."""
        condition = {"type": "result_check", "expected_result": "completed"}
        task_result = {"result": "completed"}

        result = self.engine._check_branching_condition(condition, task_result)
        self.assertTrue(result)

    @patch(
        "src.bmad_crewai.crewai_engine.BmadWorkflowEngine._execute_single_task_attempt"
    )
    def test_execute_task_with_error_recovery_success(self, mock_execute):
        """Test successful task execution with error recovery."""
        mock_execute.return_value = {"status": "success"}

        result = self.engine._execute_task_with_error_recovery(
            "test_workflow", {"agent": "test_agent"}, 0, {}
        )

        self.assertEqual(result["status"], "success")
        self.assertNotIn("recovery_attempts", result)

    @patch(
        "src.bmad_crewai.crewai_engine.BmadWorkflowEngine._execute_single_task_attempt"
    )
    def test_execute_task_with_error_recovery_retry_success(self, mock_execute):
        """Test task execution with successful retry."""
        # First call fails, second call succeeds
        mock_execute.side_effect = [
            {"status": "failed", "error": "Network error"},
            {"status": "success"},
        ]

        result = self.engine._execute_task_with_error_recovery(
            "test_workflow", {"agent": "test_agent"}, 0, {}
        )

        self.assertEqual(result["status"], "success")
        self.assertTrue(result.get("recovered"))
        self.assertEqual(result["recovery_attempts"], 1)

    @patch(
        "src.bmad_crewai.crewai_engine.BmadWorkflowEngine._execute_single_task_attempt"
    )
    def test_execute_task_with_error_recovery_max_retries_exceeded(self, mock_execute):
        """Test task execution when max retries are exceeded."""
        mock_execute.return_value = {"status": "failed", "error": "Persistent error"}

        result = self.engine._execute_task_with_error_recovery(
            "test_workflow", {"agent": "test_agent"}, 0, {}
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("Max retry attempts exceeded", result["error"])

    @patch(
        "src.bmad_crewai.crewai_engine.BmadWorkflowEngine._execute_single_task_attempt"
    )
    @patch("time.sleep")
    def test_execute_task_with_error_recovery_exponential_backoff(
        self, mock_sleep, mock_execute
    ):
        """Test exponential backoff timing in retry mechanism."""
        mock_execute.return_value = {"status": "failed", "error": "Network error"}

        self.engine._execute_task_with_error_recovery(
            "test_workflow", {"agent": "test_agent"}, 0, {}
        )

        # Check that sleep was called with exponential backoff values
        expected_calls = [1, 2, 4]  # 1 * (2^(attempt-1))
        actual_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertEqual(actual_calls, expected_calls)


if __name__ == "__main__":
    unittest.main()
