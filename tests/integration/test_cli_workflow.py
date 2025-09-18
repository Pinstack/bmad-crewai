"""Integration tests for CLI workflow execution."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.bmad_crewai.cli import CLI


class TestCLIWorkflowIntegration:
    """Integration tests for CLI workflow functionality."""

    @pytest.fixture
    def cli(self):
        """Create a CLI instance for testing."""
        return CLI()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp:
            yield Path(temp)

    @pytest.mark.asyncio
    async def test_workflow_run_command_execution(self, cli):
        """Test end-to-end workflow run command execution."""
        # Mock the CrewAI engine
        cli.command_handler.crewai_engine = Mock()
        cli.command_handler.crewai_engine.execute_workflow = AsyncMock()

        with patch("src.bmad_crewai.cli.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20250112-143022"

            # Execute workflow run command
            result = await cli.command_handler.execute_command(
                {
                    "command": "workflow",
                    "subcommand": "run",
                    "template": "test-template",
                    "params": ["--output", "test.md"],
                }
            )

            # Verify command execution
            assert result["success"] is True
            assert "workflow_id" in result
            assert "wf-20250112-143022" in result["workflow_id"]
            cli.command_handler.crewai_engine.execute_workflow.assert_called_once_with(
                "test-template", "wf-20250112-143022", ["--output", "test.md"]
            )

    @pytest.mark.asyncio
    async def test_workflow_status_command_execution(self, cli):
        """Test workflow status command execution."""
        # Mock workflow tracker
        mock_workflow = {
            "workflow_id": "wf-test",
            "status": "running",
            "workflow_name": "Test Workflow",
        }

        cli.command_handler.workflow_tracker.get_workflow_status = Mock(
            return_value=mock_workflow
        )
        cli.command_handler.workflow_tracker.get_workflow_details = Mock(
            return_value=mock_workflow
        )

        result = await cli.command_handler.execute_command(
            {"command": "workflow", "subcommand": "status", "workflow_id": "wf-test"}
        )

        assert result["workflow_id"] == "wf-test"
        assert result["status"] == "running"
        assert result["details"] == mock_workflow

    @pytest.mark.asyncio
    async def test_workflow_list_command_execution(self, cli):
        """Test workflow list command execution."""
        mock_workflows = [
            {"id": "wf-1", "status": "completed"},
            {"id": "wf-2", "status": "running"},
        ]

        cli.command_handler.workflow_tracker.list_workflows = Mock(
            return_value=mock_workflows
        )

        result = await cli.command_handler.execute_command(
            {"command": "workflow", "subcommand": "list", "filter": "all"}
        )

        assert result["total_workflows"] == 2
        assert result["filter"] == "all"
        assert result["workflows"] == mock_workflows

    @pytest.mark.asyncio
    async def test_workflow_cancel_command_execution(self, cli):
        """Test workflow cancel command execution."""
        cli.command_handler.workflow_tracker.cancel_workflow = Mock(return_value=True)

        result = await cli.command_handler.execute_command(
            {"command": "workflow", "subcommand": "cancel", "workflow_id": "wf-test"}
        )

        assert result["success"] is True
        assert "cancelled successfully" in result["message"]
        cli.command_handler.workflow_tracker.cancel_workflow.assert_called_once_with(
            "wf-test"
        )

    @pytest.mark.asyncio
    async def test_workflow_metrics_command_execution(self, cli):
        """Test workflow metrics command execution."""
        mock_progress = {
            "workflow_id": "wf-test",
            "progress_percentage": 75.0,
            "completed_tasks": 3,
            "total_tasks": 4,
        }

        cli.command_handler.workflow_tracker.get_workflow_progress = Mock(
            return_value=mock_progress
        )

        result = await cli.command_handler.execute_command(
            {"command": "workflow", "subcommand": "metrics", "workflow_id": "wf-test"}
        )

        assert result["workflow_id"] == "wf-test"
        assert result["metrics"] == mock_progress

    @pytest.mark.asyncio
    async def test_artefact_list_command_execution(self, cli):
        """Test artefact list command execution."""
        mock_artefacts = [
            {"name": "test1", "path": "docs/test1.md", "type": "stories"},
            {"name": "test2", "path": "docs/test2.md", "type": "stories"},
        ]

        cli.command_handler.artefact_writer.list_artefacts_by_type = Mock(
            return_value=mock_artefacts
        )

        result = await cli.command_handler.execute_command(
            {"command": "artefact", "subcommand": "list", "type": "stories"}
        )

        assert result["artefact_type"] == "stories"
        assert result["total_artefacts"] == 2
        assert result["artefacts"] == mock_artefacts

    @pytest.mark.asyncio
    async def test_artefact_validate_command_execution(self, cli):
        """Test artefact validate command execution."""
        mock_validation = {"decision": "PASS", "confidence_score": 90, "issues": []}

        cli.command_handler.quality_gate_manager.validate_artefact = Mock(
            return_value=mock_validation
        )

        result = await cli.command_handler.execute_command(
            {"command": "artefact", "subcommand": "validate", "path": "docs/test.md"}
        )

        assert result["artefact_path"] == "docs/test.md"
        assert result["validation_result"] == mock_validation

    @pytest.mark.asyncio
    async def test_artefact_view_command_execution(self, cli):
        """Test artefact view command execution."""
        mock_content = "# Test Document\n\nThis is test content."

        cli.command_handler.artefact_writer.read_artefact = Mock(
            return_value=mock_content
        )

        result = await cli.command_handler.execute_command(
            {"command": "artefact", "subcommand": "view", "path": "docs/test.md"}
        )

        assert result["artefact_path"] == "docs/test.md"
        assert result["content"] == mock_content

    @pytest.mark.asyncio
    async def test_config_workflow_command_execution(self, cli):
        """Test config workflow command execution."""
        mock_config = {"default_template": "test-template"}

        with patch("src.bmad_crewai.cli.ConfigManager") as mock_config_manager:
            mock_instance = Mock()
            mock_config_manager.return_value = mock_instance
            mock_instance._config = {}
            mock_instance.save = Mock()

            result = await cli.command_handler.execute_command(
                {
                    "command": "config",
                    "subcommand": "workflow",
                    "action": "set-default",
                    "params": ["test-template"],
                }
            )

            assert result["success"] is True
            assert result["default_template"] == "test-template"
            mock_instance.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_agent_command_execution(self, cli):
        """Test config agent command execution."""
        with patch("src.bmad_crewai.cli.ConfigManager") as mock_config_manager:
            mock_instance = Mock()
            mock_config_manager.return_value = mock_instance
            mock_instance._config = {"agents": {"enabled": []}}
            mock_instance.save = Mock()

            result = await cli.command_handler.execute_command(
                {
                    "command": "config",
                    "subcommand": "agent",
                    "action": "enable",
                    "params": ["dev"],
                }
            )

            assert result["success"] is True
            assert result["enabled_agent"] == "dev"
            mock_instance.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_validate_command_execution(self, cli):
        """Test config validate command execution."""
        with patch("src.bmad_crewai.cli.ConfigManager") as mock_config_manager:
            mock_instance = Mock()
            mock_config_manager.return_value = mock_instance
            mock_instance.config_file = Mock()
            mock_instance.config_file.exists.return_value = True
            mock_instance._config = {
                "bmad": {"core_path": ".bmad-core"},
                "logging": {"level": "INFO"},
                "apis": {"openai": {}},
            }
            mock_instance.get_api_key.return_value = "test-key"

            with patch("src.bmad_crewai.cli.Path") as mock_path:
                mock_path.return_value.exists.return_value = True

                result = await cli.command_handler.execute_command(
                    {"command": "config", "subcommand": "validate"}
                )

                assert "valid" in result
                assert "issues" in result
                assert "config_path" in result

    @pytest.mark.asyncio
    async def test_cli_error_handling(self, cli):
        """Test CLI error handling for various scenarios."""
        # Test invalid command
        result = await cli.command_handler.execute_command({"command": "invalid"})
        assert "error" in result

        # Test missing required parameters
        result = await cli.command_handler.execute_command(
            {"command": "workflow", "subcommand": "run"}
        )
        assert "error" in result
        assert "Template name required" in result["error"]

    def test_cli_display_integration(self, cli):
        """Test CLI display methods integration."""
        # Test various display scenarios
        with patch("builtins.print"):
            # Test workflow display
            cli._display_workflows(
                {
                    "workflows": [{"id": "wf-1", "status": "running"}],
                    "total_workflows": 1,
                }
            )

            # Test metrics display
            cli._display_metrics(
                {"aggregate_metrics": {"total_workflows": 5, "success_rate": 80.0}}
            )

            # Test config display
            cli._display_config({"workflow_config": {"default_template": "test"}})

            # Test validation display
            cli._display_validation(
                {"validation_result": {"decision": "PASS", "confidence_score": 95}}
            )

    @pytest.mark.asyncio
    async def test_cli_context_manager_integration(self, cli):
        """Test CLI context manager with real async operations."""
        with patch("src.bmad_crewai.cli.BmadCrewAI") as mock_bmad:
            mock_bmad_instance = Mock()
            mock_bmad.return_value = mock_bmad_instance
            mock_bmad_instance.close = AsyncMock()

            async with cli:
                assert cli.bmad is not None
                assert cli.command_handler is not None
                assert cli.command_handler.cli == cli

            # Verify cleanup
            mock_bmad_instance.close.assert_called_once()
            assert cli.bmad is None
