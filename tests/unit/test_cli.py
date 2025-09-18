"""Unit tests for CLI interface."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.bmad_crewai.cli import CLI, CLICommandHandler


class TestCLICommandHandler:
    """Test CLI command handler functionality."""

    @pytest.fixture
    def cli_instance(self):
        """Create a mock CLI instance."""
        cli = Mock()
        return cli

    @pytest.fixture
    def command_handler(self, cli_instance):
        """Create a command handler instance."""
        return CLICommandHandler(cli_instance)

    def test_parse_command_help(self, command_handler):
        """Test parsing help command."""
        result = command_handler.parse_command([])
        assert result["command"] == "help"
        assert result["help"] is True

    def test_parse_workflow_run_command(self, command_handler):
        """Test parsing workflow run command."""
        result = command_handler.parse_command(
            ["workflow", "run", "template1", "--param", "value"]
        )
        assert result["command"] == "workflow"
        assert result["subcommand"] == "run"
        assert result["template"] == "template1"
        assert result["params"] == ["--param", "value"]

    def test_parse_workflow_status_command(self, command_handler):
        """Test parsing workflow status command."""
        result = command_handler.parse_command(["workflow", "status", "wf-123"])
        assert result["command"] == "workflow"
        assert result["subcommand"] == "status"
        assert result["workflow_id"] == "wf-123"

    def test_parse_workflow_list_command(self, command_handler):
        """Test parsing workflow list command."""
        result = command_handler.parse_command(["workflow", "list", "active"])
        assert result["command"] == "workflow"
        assert result["subcommand"] == "list"
        assert result["filter"] == "active"

    def test_parse_artefact_list_command(self, command_handler):
        """Test parsing artefact list command."""
        result = command_handler.parse_command(["artefact", "list", "stories"])
        assert result["command"] == "artefact"
        assert result["subcommand"] == "list"
        assert result["type"] == "stories"

    def test_parse_config_workflow_command(self, command_handler):
        """Test parsing config workflow command."""
        result = command_handler.parse_command(["config", "workflow", "list"])
        assert result["command"] == "config"
        assert result["subcommand"] == "workflow"
        assert result["action"] == "list"

    @pytest.mark.asyncio
    async def test_execute_unknown_command(self, command_handler):
        """Test executing unknown command."""
        result = await command_handler.execute_command({"command": "unknown"})
        assert "error" in result
        assert "Unknown command" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_unknown_workflow_subcommand(self, command_handler):
        """Test executing unknown workflow subcommand."""
        result = await command_handler.execute_command(
            {"command": "workflow", "subcommand": "unknown"}
        )
        assert "error" in result
        assert "Unknown workflow subcommand" in result["error"]

    @pytest.mark.asyncio
    async def test_workflow_run_missing_template(self, command_handler):
        """Test workflow run without template."""
        result = await command_handler.execute_command(
            {"command": "workflow", "subcommand": "run"}
        )
        assert "error" in result
        assert "Template name required" in result["error"]

    @pytest.mark.asyncio
    @patch("src.bmad_crewai.cli.datetime")
    async def test_workflow_run_success(self, mock_datetime, command_handler):
        """Test successful workflow run."""
        mock_datetime.now.return_value.strftime.return_value = "20250112-143022"

        # Mock the CrewAI engine
        command_handler.crewai_engine = Mock()
        command_handler.crewai_engine.execute_workflow = AsyncMock()

        result = await command_handler.execute_command(
            {
                "command": "workflow",
                "subcommand": "run",
                "template": "test-template",
                "params": ["--output", "test.md"],
            }
        )

        assert result["success"] is True
        assert "workflow_id" in result
        assert "wf-20250112-143022" in result["workflow_id"]
        command_handler.crewai_engine.execute_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_cancel_missing_id(self, command_handler):
        """Test workflow cancel without ID."""
        result = await command_handler.execute_command(
            {"command": "workflow", "subcommand": "cancel"}
        )
        assert "error" in result
        assert "Workflow ID required" in result["error"]

    @pytest.mark.asyncio
    async def test_artefact_validate_missing_path(self, command_handler):
        """Test artefact validate without path."""
        result = await command_handler.execute_command(
            {"command": "artefact", "subcommand": "validate"}
        )
        assert "error" in result
        assert "Artefact path required" in result["error"]

    @pytest.mark.asyncio
    async def test_artefact_view_missing_path(self, command_handler):
        """Test artefact view without path."""
        result = await command_handler.execute_command(
            {"command": "artefact", "subcommand": "view"}
        )
        assert "error" in result
        assert "Artefact path required" in result["error"]

    def test_list_workflow_templates_no_path(self, command_handler):
        """Test listing workflow templates when path doesn't exist."""
        with patch("src.bmad_crewai.cli.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            templates = command_handler._list_workflow_templates()
            assert templates == []

    def test_list_available_agents_no_path(self, command_handler):
        """Test listing agents when path doesn't exist."""
        with patch("src.bmad_crewai.cli.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            agents = command_handler._list_available_agents()
            assert agents == []

    def test_get_help_text(self, command_handler):
        """Test help text generation."""
        help_text = command_handler._get_help_text()
        assert "BMAD CrewAI CLI" in help_text
        assert "workflow run" in help_text
        assert "artefact list" in help_text
        assert "config workflow" in help_text


class TestCLI:
    """Test CLI class functionality."""

    @pytest.fixture
    def cli(self):
        """Create a CLI instance."""
        return CLI()

    def test_cli_initialization(self, cli):
        """Test CLI initialization."""
        assert cli.bmad is None
        assert cli.command_handler is not None

    @pytest.mark.asyncio
    async def test_cli_context_manager(self, cli):
        """Test CLI context manager."""
        async with cli:
            assert cli.bmad is not None
            assert cli.command_handler is not None

        assert cli.bmad is None

    def test_run_no_args(self, cli):
        """Test CLI run with no arguments."""
        with patch("builtins.print") as mock_print:
            cli.run()
            mock_print.assert_called()

    def test_run_with_args(self, cli):
        """Test CLI run with arguments."""
        with patch.object(cli, "run_async_command") as mock_run_async:
            with patch("sys.argv", ["bmad-crewai", "help"]):
                cli.run()
                mock_run_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_async_command_error_handling(self, cli):
        """Test async command error handling."""
        with patch.object(cli.command_handler, "execute_command") as mock_execute:
            mock_execute.side_effect = Exception("Test error")

            with patch("sys.exit") as mock_exit:
                await cli.run_async_command({"command": "test"})
                mock_exit.assert_called_once_with(1)

    def test_display_command_result_success(self, cli):
        """Test displaying successful command result."""
        with patch("builtins.print") as mock_print:
            cli._display_command_result({"success": True, "message": "Test success"})
            mock_print.assert_any_call("✅ Success!")
            mock_print.assert_any_call("Test success")

    def test_display_command_result_error(self, cli):
        """Test displaying error command result."""
        with patch("builtins.print") as mock_print:
            cli._display_command_result({"error": "Test error"})
            mock_print.assert_any_call("❌ Error: Test error")

    def test_display_command_result_help(self, cli):
        """Test displaying help command result."""
        with patch("builtins.print") as mock_print:
            cli._display_command_result({"help": True, "usage": "Help text"})
            mock_print.assert_called_with("Usage: Help text")

    def test_display_workflows(self, cli):
        """Test displaying workflow results."""
        workflows = [
            {"id": "wf-1", "status": "completed", "template": "test"},
            {"id": "wf-2", "status": "running", "template": "test2"},
        ]

        with patch("builtins.print") as mock_print:
            cli._display_workflows({"workflows": workflows, "total_workflows": 2})
            mock_print.assert_any_call("\n⚙️  Workflows (all): 2")

    def test_display_metrics_aggregate(self, cli):
        """Test displaying aggregate metrics."""
        metrics = {
            "total_workflows": 10,
            "completed_workflows": 7,
            "failed_workflows": 2,
            "active_workflows": 1,
            "success_rate": 70.0,
        }

        with patch("builtins.print") as mock_print:
            cli._display_metrics({"aggregate_metrics": metrics})
            mock_print.assert_any_call("Total Workflows: 10")

    def test_display_validation(self, cli):
        """Test displaying validation results."""
        validation = {
            "decision": "PASS",
            "confidence_score": 85,
            "issues": ["Minor issue"],
        }

        with patch("builtins.print") as mock_print:
            cli._display_validation({"validation_result": validation})
            mock_print.assert_any_call("Decision: ✅ PASS")

    def test_print_help(self, cli):
        """Test help printing."""
        with patch.object(cli.command_handler, "_get_help_text") as mock_get_help:
            mock_get_help.return_value = "Help text"
            with patch("builtins.print") as mock_print:
                cli.print_help()
                mock_print.assert_called_with("Help text")
