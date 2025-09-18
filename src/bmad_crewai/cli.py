"""Command-line interface for BMAD CrewAI."""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .api_client import RateLimitInfo
from .artefact_writer import BMADArtefactWriter
from .config import ConfigManager
from .core import BmadCrewAI
from .crewai_engine import CrewAIOrchestrationEngine as CrewAIEngine
from .exceptions import BmadCrewAIError
from .quality_gate_manager import QualityGateManager
from .workflow_manager import WorkflowStateTracker, WorkflowStatus

logger = logging.getLogger(__name__)


class CLICommandHandler:
    """Handles CLI command parsing, validation, and execution routing."""

    def __init__(self, cli_instance):
        self.cli = cli_instance
        self.workflow_tracker = WorkflowStateTracker()
        self.artefact_writer = BMADArtefactWriter()
        self.quality_gate_manager = QualityGateManager()
        self.crewai_engine = CrewAIEngine()

    def parse_command(self, args: List[str]) -> Dict[str, Any]:
        """Parse command arguments and validate structure."""
        if not args:
            return {"command": "help", "args": {}, "help": True}

        command = args[0]

        # Parse subcommands and arguments
        if command == "workflow":
            return self._parse_workflow_command(args[1:])
        elif command == "artefact":
            return self._parse_artefact_command(args[1:])
        elif command == "config":
            return self._parse_config_command(args[1:])
        else:
            return {"command": command, "args": args[1:], "help": False}

    def _parse_workflow_command(self, args: List[str]) -> Dict[str, Any]:
        """Parse workflow subcommands."""
        if not args:
            return {"command": "workflow", "subcommand": "help", "args": {}}

        subcommand = args[0]
        sub_args = args[1:]

        if subcommand == "run":
            return {
                "command": "workflow",
                "subcommand": "run",
                "template": sub_args[0] if sub_args else None,
                "params": sub_args[1:] if len(sub_args) > 1 else [],
            }
        elif subcommand == "status":
            return {
                "command": "workflow",
                "subcommand": "status",
                "workflow_id": sub_args[0] if sub_args else None,
            }
        elif subcommand == "list":
            return {
                "command": "workflow",
                "subcommand": "list",
                "filter": sub_args[0] if sub_args else None,
            }
        elif subcommand == "cancel":
            return {
                "command": "workflow",
                "subcommand": "cancel",
                "workflow_id": sub_args[0] if sub_args else None,
            }
        elif subcommand == "metrics":
            return {
                "command": "workflow",
                "subcommand": "metrics",
                "workflow_id": sub_args[0] if sub_args else None,
            }

        return {"command": "workflow", "subcommand": subcommand, "args": sub_args}

    def _parse_artefact_command(self, args: List[str]) -> Dict[str, Any]:
        """Parse artefact subcommands."""
        if not args:
            return {"command": "artefact", "subcommand": "help", "args": {}}

        subcommand = args[0]
        sub_args = args[1:]

        if subcommand == "list":
            return {
                "command": "artefact",
                "subcommand": "list",
                "type": sub_args[0] if sub_args else None,
            }
        elif subcommand == "validate":
            return {
                "command": "artefact",
                "subcommand": "validate",
                "path": sub_args[0] if sub_args else None,
            }
        elif subcommand == "view":
            return {
                "command": "artefact",
                "subcommand": "view",
                "path": sub_args[0] if sub_args else None,
            }

        return {"command": "artefact", "subcommand": subcommand, "args": sub_args}

    def _parse_config_command(self, args: List[str]) -> Dict[str, Any]:
        """Parse config subcommands."""
        if not args:
            return {"command": "config", "subcommand": "help", "args": {}}

        subcommand = args[0]
        sub_args = args[1:]

        if subcommand == "workflow":
            return {
                "command": "config",
                "subcommand": "workflow",
                "action": sub_args[0] if sub_args else None,
                "params": sub_args[1:],
            }
        elif subcommand == "agent":
            return {
                "command": "config",
                "subcommand": "agent",
                "action": sub_args[0] if sub_args else None,
                "params": sub_args[1:],
            }
        elif subcommand == "validate":
            return {"command": "config", "subcommand": "validate"}

        return {"command": "config", "subcommand": subcommand, "args": sub_args}

    async def execute_command(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parsed command and return results."""
        command = parsed_command["command"]

        try:
            if command == "workflow":
                return await self._execute_workflow_command(parsed_command)
            elif command == "artefact":
                return await self._execute_artefact_command(parsed_command)
            elif command == "config":
                return await self._execute_config_command(parsed_command)
            elif command == "help":
                return self._execute_help_command(parsed_command)
            else:
                return {"error": f"Unknown command: {command}"}
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {"error": str(e)}

    async def _execute_workflow_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow commands."""
        subcommand = cmd["subcommand"]

        if subcommand == "run":
            return await self._workflow_run(cmd)
        elif subcommand == "status":
            return await self._workflow_status(cmd)
        elif subcommand == "list":
            return await self._workflow_list(cmd)
        elif subcommand == "cancel":
            return await self._workflow_cancel(cmd)
        elif subcommand == "metrics":
            return await self._workflow_metrics(cmd)
        else:
            return {"error": f"Unknown workflow subcommand: {subcommand}"}

    async def _execute_artefact_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute artefact commands."""
        subcommand = cmd["subcommand"]

        if subcommand == "list":
            return await self._artefact_list(cmd)
        elif subcommand == "validate":
            return await self._artefact_validate(cmd)
        elif subcommand == "view":
            return await self._artefact_view(cmd)
        else:
            return {"error": f"Unknown artefact subcommand: {subcommand}"}

    async def _execute_config_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute config commands."""
        subcommand = cmd["subcommand"]

        if subcommand == "workflow":
            return await self._config_workflow(cmd)
        elif subcommand == "agent":
            return await self._config_agent(cmd)
        elif subcommand == "validate":
            return await self._config_validate(cmd)
        else:
            return {"error": f"Unknown config subcommand: {subcommand}"}

    def _execute_help_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute help command."""
        return {"help": True, "usage": self._get_help_text()}

    # Workflow command implementations
    async def _workflow_run(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow run command."""
        template = cmd.get("template")
        if not template:
            return {"error": "Template name required for workflow run"}

        # Initialize workflow execution
        workflow_id = f"wf-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        try:
            # Start workflow execution through CrewAI engine
            await self.crewai_engine.execute_workflow(
                template, workflow_id, cmd.get("params", [])
            )

            return {
                "success": True,
                "workflow_id": workflow_id,
                "message": f"Workflow {workflow_id} started with template {template}",
            }
        except Exception as e:
            return {"error": f"Failed to start workflow: {str(e)}"}

    async def _workflow_status(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow status command."""
        workflow_id = cmd.get("workflow_id")

        if workflow_id:
            # Get specific workflow status
            status = self.workflow_tracker.get_workflow_status(workflow_id)
            return {
                "workflow_id": workflow_id,
                "status": status.value if hasattr(status, "value") else str(status),
                "details": self.workflow_tracker.get_workflow_details(workflow_id),
            }
        else:
            # Get all active workflows
            active_workflows = self.workflow_tracker.get_active_workflows()
            return {
                "active_workflows": len(active_workflows),
                "workflows": active_workflows,
            }

    async def _workflow_list(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow list command."""
        workflow_filter = cmd.get("filter")
        workflows = self.workflow_tracker.list_workflows(filter_type=workflow_filter)

        return {
            "total_workflows": len(workflows),
            "filter": workflow_filter,
            "workflows": workflows,
        }

    async def _workflow_cancel(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow cancel command."""
        workflow_id = cmd.get("workflow_id")
        if not workflow_id:
            return {"error": "Workflow ID required for cancellation"}

        try:
            success = self.workflow_tracker.cancel_workflow(workflow_id)
            if success:
                return {
                    "success": True,
                    "message": f"Workflow {workflow_id} cancelled successfully",
                }
            else:
                return {
                    "error": f"Workflow {workflow_id} could not be cancelled (not found or not active)"
                }
        except Exception as e:
            return {"error": f"Failed to cancel workflow: {str(e)}"}

    async def _workflow_metrics(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow metrics command."""
        workflow_id = cmd.get("workflow_id")

        try:
            if workflow_id:
                # Get metrics for specific workflow
                progress = self.workflow_tracker.get_workflow_progress(workflow_id)
                if progress:
                    return {"workflow_id": workflow_id, "metrics": progress}
                else:
                    return {"error": f"No metrics found for workflow {workflow_id}"}
            else:
                # Get aggregate metrics for all workflows
                all_workflows = self.workflow_tracker.list_workflows()
                total_workflows = len(all_workflows)
                completed_workflows = len(
                    [w for w in all_workflows if w.get("status") == "completed"]
                )
                failed_workflows = len(
                    [w for w in all_workflows if w.get("status") == "failed"]
                )
                active_workflows = len(
                    [
                        w
                        for w in all_workflows
                        if w.get("status") in ["running", "pending"]
                    ]
                )

                return {
                    "aggregate_metrics": {
                        "total_workflows": total_workflows,
                        "completed_workflows": completed_workflows,
                        "failed_workflows": failed_workflows,
                        "active_workflows": active_workflows,
                        "success_rate": (
                            (completed_workflows / total_workflows * 100)
                            if total_workflows > 0
                            else 0
                        ),
                    }
                }
        except Exception as e:
            return {"error": f"Failed to get workflow metrics: {str(e)}"}

    # Artefact command implementations
    async def _artefact_list(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute artefact list command."""
        artefact_type = cmd.get("type")

        if artefact_type:
            artefacts = self.artefact_writer.list_artefacts_by_type(artefact_type)
        else:
            artefacts = self.artefact_writer.list_all_artefacts()

        return {
            "artefact_type": artefact_type,
            "total_artefacts": len(artefacts),
            "artefacts": artefacts,
        }

    async def _artefact_validate(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute artefact validate command."""
        path = cmd.get("path")
        if not path:
            return {"error": "Artefact path required for validation"}

        try:
            validation_result = self.quality_gate_manager.validate_artefact(path)
            return {"artefact_path": path, "validation_result": validation_result}
        except Exception as e:
            return {"error": f"Artefact validation failed: {str(e)}"}

    async def _artefact_view(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute artefact view command."""
        path = cmd.get("path")
        if not path:
            return {"error": "Artefact path required for viewing"}

        try:
            content = self.artefact_writer.read_artefact(path)
            return {"artefact_path": path, "content": content}
        except Exception as e:
            return {"error": f"Artefact viewing failed: {str(e)}"}

    # Config command implementations
    async def _config_workflow(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute config workflow command."""
        action = cmd.get("action")
        if not action:
            return {"error": "Action required for workflow config"}

        # Handle workflow configuration actions
        if action == "list":
            templates = self._list_workflow_templates()
            return {"templates": templates}
        elif action == "set-default":
            template = cmd.get("params", [None])[0]
            if not template:
                return {"error": "Template name required"}
            # Set default workflow template in config
            config_manager = ConfigManager()
            config = config_manager._config
            if "workflow" not in config:
                config["workflow"] = {}
            config["workflow"]["default_template"] = template
            config_manager.save()
            return {"success": True, "default_template": template}
        elif action == "show":
            # Show current workflow configuration
            config_manager = ConfigManager()
            config = config_manager._config
            workflow_config = config.get("workflow", {})
            return {"workflow_config": workflow_config}
        else:
            return {"error": f"Unknown workflow config action: {action}"}

    async def _config_agent(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute config agent command."""
        action = cmd.get("action")
        if not action:
            return {"error": "Action required for agent config"}

        # Handle agent configuration actions
        if action == "list":
            agents = self._list_available_agents()
            return {"agents": agents}
        elif action == "enable":
            agent = cmd.get("params", [None])[0]
            if not agent:
                return {"error": "Agent name required"}
            # Enable specific agent in config
            config_manager = ConfigManager()
            config = config_manager._config
            if "agents" not in config:
                config["agents"] = {}
            if "enabled" not in config["agents"]:
                config["agents"]["enabled"] = []
            if agent not in config["agents"]["enabled"]:
                config["agents"]["enabled"].append(agent)
            config_manager.save()
            return {"success": True, "enabled_agent": agent}
        elif action == "disable":
            agent = cmd.get("params", [None])[0]
            if not agent:
                return {"error": "Agent name required"}
            # Disable specific agent in config
            config_manager = ConfigManager()
            config = config_manager._config
            if "agents" in config and "enabled" in config["agents"]:
                if agent in config["agents"]["enabled"]:
                    config["agents"]["enabled"].remove(agent)
                    config_manager.save()
                    return {"success": True, "disabled_agent": agent}
            return {"error": f"Agent {agent} is not currently enabled"}
        elif action == "show":
            # Show current agent configuration
            config_manager = ConfigManager()
            config = config_manager._config
            agent_config = config.get("agents", {})
            return {"agent_config": agent_config}
        else:
            return {"error": f"Unknown agent config action: {action}"}

    async def _config_validate(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute config validate command."""
        try:
            config_manager = ConfigManager()
            config_file = config_manager.config_file

            # Check if config file exists
            if not config_file.exists():
                return {"valid": False, "issues": ["Configuration file not found"]}

            # Validate configuration structure
            config = config_manager._config
            issues = []

            # Check required sections
            required_sections = ["bmad", "logging", "apis"]
            for section in required_sections:
                if section not in config:
                    issues.append(f"Missing required section: {section}")

            # Check BMAD core path
            bmad_path = Path(config.get("bmad", {}).get("core_path", ".bmad-core"))
            if not bmad_path.exists():
                issues.append(f"BMAD core path does not exist: {bmad_path}")

            # Check API keys for configured providers
            apis = config.get("apis", {})
            for provider in apis:
                if not config_manager.get_api_key(provider):
                    issues.append(f"API key not configured for: {provider}")

            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "config_path": str(config_file),
            }
        except Exception as e:
            return {"valid": False, "issues": [f"Validation error: {str(e)}"]}

    def _list_workflow_templates(self) -> List[str]:
        """List available workflow templates."""
        templates_path = Path(".bmad-core/templates")
        if not templates_path.exists():
            return []

        templates = []
        for file_path in templates_path.rglob("*.yaml"):
            templates.append(file_path.stem)

        return templates

    def _list_available_agents(self) -> List[str]:
        """List available agents."""
        agents_path = Path(".bmad-core/agents")
        if not agents_path.exists():
            return []

        agents = []
        for file_path in agents_path.rglob("*.md"):
            agents.append(file_path.stem)

        return agents

    def _get_help_text(self) -> str:
        """Get comprehensive help text."""
        return """
BMAD CrewAI CLI - Comprehensive Workflow Management

COMMANDS:

  workflow run <template> [params...]    Execute workflow with template selection
  workflow status [workflow_id]          Show workflow execution status
  workflow list [filter]                 List workflows (active/completed/all)
  workflow cancel <workflow_id>          Cancel a running workflow
  workflow metrics [workflow_id]         Show workflow performance metrics

  artefact list [type]                   List generated artefacts by type
  artefact validate <path>               Validate artefact quality
  artefact view <path>                   Display artefact contents

  config workflow <action> [params...]   Manage workflow configurations
  config agent <action> [params...]      Manage agent configurations
  config validate                         Validate current configuration

  setup                                  Initial setup and configuration
  status                                 Show current system status
  help                                   Show this help message

EXAMPLES:

  bmad-crewai workflow run prd-template --output docs/prd.md
  bmad-crewai workflow status wf-20250112-143022
  bmad-crewai workflow list active
  bmad-crewai workflow cancel wf-20250112-143022
  bmad-crewai workflow metrics
  bmad-crewai artefact list stories
  bmad-crewai config workflow list
  bmad-crewai config agent enable dev
  bmad-crewai config validate

For detailed help on any command, run: bmad-crewai <command> --help
        """


class CLI:
    """Command-line interface for BMAD CrewAI."""

    def __init__(self):
        self.bmad = None
        self.command_handler = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.bmad = BmadCrewAI()
        self.command_handler = CLICommandHandler(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.bmad:
            await self.bmad.close()

    def run(self):
        """Run the CLI with enhanced command parsing."""
        if len(sys.argv) < 2:
            self.print_help()
            return

        # Parse command using new handler
        args = sys.argv[1:]
        parsed_command = self.command_handler.parse_command(args)

        # Run async commands
        asyncio.run(self.run_async_command(parsed_command))

    async def run_async_command(self, parsed_command: Dict[str, Any]):
        """Run async command with parsed structure."""
        try:
            # Execute command using handler
            result = await self.command_handler.execute_command(parsed_command)

            # Handle results
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                sys.exit(1)
            elif result.get("help"):
                print(result["usage"])
            else:
                self._display_command_result(result)

        except BmadCrewAIError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            logger.exception("CLI execution failed")
            sys.exit(1)

    def _display_command_result(self, result: Dict[str, Any]):
        """Display command execution results in user-friendly format."""
        if result.get("success"):
            print("✅ Success!")
            if "message" in result:
                print(result["message"])
            if "workflow_id" in result:
                print(f"Workflow ID: {result['workflow_id']}")

        elif "artefacts" in result:
            self._display_artefacts(result)
        elif "workflows" in result:
            self._display_workflows(result)
        elif "templates" in result:
            self._display_templates(result)
        elif "agents" in result:
            self._display_agents(result)
        elif "validation_result" in result:
            self._display_validation(result)
        elif "content" in result:
            self._display_content(result)
        elif "aggregate_metrics" in result or "metrics" in result:
            self._display_metrics(result)
        elif (
            "workflow_config" in result or "agent_config" in result or "valid" in result
        ):
            self._display_config(result)
        else:
            # Generic result display
            for key, value in result.items():
                if key not in ["success", "error", "help"]:
                    print(f"{key.replace('_', ' ').title()}: {value}")

    def _display_artefacts(self, result: Dict[str, Any]):
        """Display artefact listing results."""
        artefact_type = result.get("artefact_type", "all")
        print(f"\n📄 Artefacts ({artefact_type}):")
        print("-" * 50)

        artefacts = result.get("artefacts", [])
        if not artefacts:
            print("No artefacts found.")
            return

        for artefact in artefacts:
            print(f"• {artefact.get('name', 'Unknown')}")
            if "path" in artefact:
                print(f"  Path: {artefact['path']}")
            if "type" in artefact:
                print(f"  Type: {artefact['type']}")
            if "size" in artefact:
                print(f"  Size: {artefact['size']} bytes")
            print()

    def _display_workflows(self, result: Dict[str, Any]):
        """Display workflow listing results."""
        total = result.get("total_workflows", 0)
        filter_type = result.get("filter", "all")

        print(f"\n⚙️  Workflows ({filter_type}): {total}")
        print("-" * 50)

        workflows = result.get("workflows", [])
        if not workflows:
            print("No workflows found.")
            return

        for workflow in workflows:
            status = workflow.get("status", "unknown")
            status_icon = {
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "pending": "⏳",
                "cancelled": "🚫",
            }.get(status, "❓")

            workflow_id = workflow.get("id") or workflow.get("workflow_id", "Unknown")
            print(f"{status_icon} {workflow_id}")
            print(f"  Status: {status}")
            if "template" in workflow:
                print(f"  Template: {workflow['template']}")
            if "start_time" in workflow:
                print(f"  Started: {workflow['start_time']}")
            if "workflow_name" in workflow:
                print(f"  Name: {workflow['workflow_name']}")
            print()

    def _display_metrics(self, result: Dict[str, Any]):
        """Display workflow metrics results."""
        if "aggregate_metrics" in result:
            metrics = result["aggregate_metrics"]
            print(f"\n📊 Workflow Metrics Summary")
            print("-" * 40)
            print(f"Total Workflows: {metrics.get('total_workflows', 0)}")
            print(f"Active: {metrics.get('active_workflows', 0)}")
            print(f"Completed: {metrics.get('completed_workflows', 0)}")
            print(f"Failed: {metrics.get('failed_workflows', 0)}")
            print(f"Success Rate: {metrics.get('success_rate', 0):.1f}%")
        elif "metrics" in result:
            metrics = result["metrics"]
            workflow_id = result.get("workflow_id", "Unknown")
            print(f"\n📊 Metrics for Workflow: {workflow_id}")
            print("-" * 40)
            print(f"Status: {metrics.get('status', 'Unknown')}")
            print(f"Progress: {metrics.get('progress_percentage', 0):.1f}%")
            print(f"Total Tasks: {metrics.get('total_tasks', 0)}")
            print(f"Completed: {metrics.get('completed_tasks', 0)}")
            print(f"Running: {metrics.get('running_tasks', 0)}")
            print(f"Failed: {metrics.get('failed_tasks', 0)}")
            if "duration" in metrics and metrics["duration"]:
                print(f"Duration: {metrics['duration']:.2f}s")
        else:
            print("\n📊 No metrics data available")

    def _display_templates(self, result: Dict[str, Any]):
        """Display template listing results."""
        templates = result.get("templates", [])
        print(f"\n📋 Available Templates: {len(templates)}")
        print("-" * 30)

        if not templates:
            print("No templates found in .bmad-core/templates/")
            return

        for template in templates:
            print(f"• {template}")

    def _display_agents(self, result: Dict[str, Any]):
        """Display agent listing results."""
        agents = result.get("agents", [])
        print(f"\n🤖 Available Agents: {len(agents)}")
        print("-" * 25)

        if not agents:
            print("No agents found in .bmad-core/agents/")
            return

        for agent in agents:
            print(f"• {agent}")

    def _display_validation(self, result: Dict[str, Any]):
        """Display validation results."""
        path = result.get("artefact_path", "Unknown")
        validation = result.get("validation_result", {})

        print(f"\n🔍 Validation Results for: {path}")
        print("-" * 50)

        if "decision" in validation:
            decision = validation["decision"]
            icon = {"PASS": "✅", "CONCERNS": "⚠️", "FAIL": "❌"}.get(decision, "❓")
            print(f"Decision: {icon} {decision}")

        if "confidence_score" in validation:
            print(f"Confidence: {validation['confidence_score']:.1f}%")

        if "issues" in validation and validation["issues"]:
            print("\nIssues Found:")
            for issue in validation["issues"]:
                print(f"• {issue}")

    def _display_content(self, result: Dict[str, Any]):
        """Display artefact content."""
        path = result.get("artefact_path", "Unknown")
        content = result.get("content", "")

        print(f"\n📖 Content of: {path}")
        print("=" * 50)
        print(content)

    def _display_config(self, result: Dict[str, Any]):
        """Display configuration results."""
        if "workflow_config" in result:
            config = result["workflow_config"]
            print(f"\n⚙️  Workflow Configuration")
            print("-" * 30)
            if config:
                for key, value in config.items():
                    print(f"{key}: {value}")
            else:
                print("No workflow configuration set.")
        elif "agent_config" in result:
            config = result["agent_config"]
            print(f"\n🤖 Agent Configuration")
            print("-" * 25)
            if config:
                enabled = config.get("enabled", [])
                if enabled:
                    print("Enabled agents:")
                    for agent in enabled:
                        print(f"  • {agent}")
                else:
                    print("No agents enabled.")
            else:
                print("No agent configuration set.")
        elif "valid" in result:
            valid = result["valid"]
            issues = result.get("issues", [])
            config_path = result.get("config_path", "Unknown")

            print(f"\n🔍 Configuration Validation: {config_path}")
            print("-" * 50)

            if valid:
                print("✅ Configuration is valid!")
            else:
                print("❌ Configuration has issues:")
                for issue in issues:
                    print(f"  • {issue}")

            if issues:
                print("\n💡 Suggestions:")
                print("  • Run 'bmad-crewai setup' to fix configuration issues")
                print("  • Check BMAD core installation")
                print("  • Verify API keys are properly configured")

    def print_help(self):
        """Print comprehensive help information."""
        print(self.command_handler._get_help_text())

    async def handle_setup(self):
        """Handle initial setup."""
        print("BMAD CrewAI Setup")
        print("==================")

        # Check if BMAD core exists
        bmad_core_path = Path(".bmad-core")
        if not bmad_core_path.exists():
            print("❌ BMAD core not found. Please run 'npx bmad-method install' first.")
            return

        print("✅ BMAD core found")

        # Check Python environment
        try:
            __import__("aiohttp")
            __import__("keyring")

            print("✅ Required packages available")
        except ImportError as e:
            print(f"❌ Missing required packages: {e}")
            print("Run: pip install aiohttp keyring cryptography")
            return

        # Create configuration
        config_manager = ConfigManager()

        # Prompt for API keys
        print("\nAPI Configuration:")
        providers = ["openai", "anthropic", "google"]

        for provider in providers:
            if input(f"Configure {provider.upper()} API key? (y/n): ").lower() == "y":
                api_key = input(f"Enter {provider.upper()} API key: ").strip()
                if api_key:
                    config_manager.store_api_key(provider, api_key)
                    print(f"✅ {provider.upper()} API key stored securely")

        # Save configuration
        config_manager.save()
        print("\n✅ Setup complete!")
        print("\nNext steps:")
        print("1. Run 'bmad-crewai status' to verify configuration")
        print("2. Run 'bmad-crewai test-api <provider>' to test API connections")

    async def handle_config(self):
        """Handle configuration management."""
        if len(sys.argv) < 3:
            print("Usage: bmad-crewai config <subcommand>")
            print("Subcommands: set-api-key, get-api-key, show")
            return

        subcommand = sys.argv[2]
        config_manager = ConfigManager()

        if subcommand == "set-api-key":
            if len(sys.argv) < 5:
                print("Usage: bmad-crewai config set-api-key <provider> <api-key>")
                return
            provider = sys.argv[3]
            api_key = sys.argv[4]
            config_manager.store_api_key(provider, api_key)
            print(f"✅ API key for {provider} stored securely")

        elif subcommand == "get-api-key":
            if len(sys.argv) < 4:
                print("Usage: bmad-crewai config get-api-key <provider>")
                return
            provider = sys.argv[3]
            api_key = config_manager.get_api_key(provider)
            if api_key:
                # Mask the key for security
                masked = api_key[:8] + "*" * (len(api_key) - 16) + api_key[-8:]
                print(f"✅ API key for {provider}: {masked}")
            else:
                print(f"❌ No API key found for {provider}")

        elif subcommand == "show":
            config = config_manager._config
            print("Current Configuration:")
            print("======================")
            print(f"BMAD Core Path: {config['bmad']['core_path']}")
            print(f"QA Location: {config['bmad']['qa_location']}")
            print(f"Stories Location: {config['bmad']['stories_location']}")
            print(f"Log Level: {config['logging']['level']}")
            print("\nAPI Providers:")
            for provider, api_config in config["apis"].items():
                has_key = config_manager.get_api_key(provider) is not None
                print(
                    f"  {provider}: {'✅ Configured' if has_key else '❌ Not configured'}"
                )

        else:
            print(f"Unknown subcommand: {subcommand}")

    async def handle_test_api(self):
        """Handle API testing with rate limiting."""
        if len(sys.argv) < 3:
            print("Usage: bmad-crewai test-api <provider>")
            return

        provider = sys.argv[2]

        async with self as cli:
            try:
                print(f"Testing {provider.upper()} API connection...")
                print("(This will test rate limiting with multiple requests)")

                # Test basic connectivity
                if provider == "openai":
                    url = "https://api.openai.com/v1/models"
                    headers = {
                        "Authorization": f"Bearer "
                        f"{cli.bmad.config_manager.get_api_key(provider)}"
                    }
                elif provider == "anthropic":
                    url = "https://api.anthropic.com/v1/messages"
                    headers = {
                        "x-api-key": cli.bmad.config_manager.get_api_key(provider)
                    }
                else:
                    print(f"❌ Testing not implemented for {provider}")
                    return

                # Make test requests to demonstrate rate limiting
                for i in range(3):
                    try:
                        print(f"\nRequest {i + 1}/3:")
                        response = await cli.bmad.make_api_request(
                            provider, "get", url, headers=headers
                        )
                        print(f"✅ Status: {response.status}")
                        requests_made = cli.bmad.rate_limiter._rate_limits.get(
                            provider, RateLimitInfo()
                        ).requests_made
                        print(f"✅ Rate limit OK - {requests_made} requests made")

                    except Exception as e:
                        print(f"❌ Error: {e}")
                        if "rate limit" in str(e).lower():
                            print("   (Rate limiting is working correctly)")
                        break

                    # Small delay between requests
                    await asyncio.sleep(1)

                print("\n✅ API testing complete!")

            except Exception as e:
                print(f"❌ API test failed: {e}")

    async def handle_status(self):
        """Handle status display."""
        print("BMAD CrewAI Status")
        print("==================")

        # Check BMAD core
        bmad_core_path = Path(".bmad-core")
        print(f"BMAD Core: {'✅ Found' if bmad_core_path.exists() else '❌ Not found'}")

        # Check configuration
        config_manager = ConfigManager()
        config_file = config_manager.config_file
        print(
            f"Config File: {'✅ Exists' if config_file.exists() else '❌ Not found'} "
            f"({config_file})"
        )

        # Check credentials
        cred_file = Path.home() / ".bmad-crewai" / "credentials.json"
        print(f"Credentials: {'✅ Stored' if cred_file.exists() else '❌ Not found'}")

        # Check API configurations
        apis = config_manager._config.get("apis", {})
        if apis:
            print("\nAPI Providers:")
            for provider, api_config in apis.items():
                has_key = config_manager.get_api_key(provider) is not None
                print(f"  {provider}: {'✅ Key available' if has_key else '❌ No key'}")
        else:
            print("\nAPI Providers: None configured")

        print("\nTo configure:")
        print("1. Run 'bmad-crewai setup' for initial setup")
        print(
            "2. Run 'bmad-crewai config set-api-key <provider> <key>' "
            "to add API keys"
        )
        print("3. Run 'bmad-crewai test-api <provider>' to test connections")


def main():
    """Main CLI entry point."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
