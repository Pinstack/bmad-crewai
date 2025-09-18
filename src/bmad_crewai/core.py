"""Main BMAD CrewAI integration orchestrator."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import yaml

from .agent_registry import AgentRegistry
from .agent_wrappers import BmadAgentRegistry
from .api_client import APIClient, APIError, RateLimiter, RateLimitError
from .artefact_manager import ArtefactManager
from .artefact_writer import BMADArtefactWriter
from .checklist_executor import ChecklistExecutor
from .config import APIConfig, ConfigManager

# CrewAI Orchestration Components
from .crewai_engine import CrewAIOrchestrationEngine
from .development_tester import DevelopmentTester
from .error_handler import BmadErrorHandler
from .exceptions import TemplateError
from .quality_gate_manager import QualityGateManager
from .template_manager import TemplateInfo, TemplateManager
from .workflow_manager import BmadWorkflowManager

logger = logging.getLogger(__name__)


class BmadCrewAI:
    """Main BMAD CrewAI integration class."""

    def __init__(self, config_file: Optional[str] = None):
        # Initialize logger first
        self.logger = logging.getLogger(__name__)

        self.config_manager = ConfigManager(config_file)
        self.rate_limiter = RateLimiter()
        self.api_clients: Dict[str, APIClient] = {}
        self.templates: Dict[str, TemplateInfo] = {}

        # Initialize managers
        self.agent_registry = AgentRegistry()
        self.artefact_manager = ArtefactManager()
        self.development_tester = DevelopmentTester()
        self.quality_gate_manager = QualityGateManager()
        self.template_manager = TemplateManager()

        # Initialize CrewAI orchestration components
        self.crewai_engine = CrewAIOrchestrationEngine(self.logger)
        self.bmad_agent_registry = BmadAgentRegistry(self.logger)
        self.workflow_manager = BmadWorkflowManager(self.crewai_engine, self.logger)
        self.error_handler = BmadErrorHandler(self.logger)

        # Legacy attributes for backward compatibility
        self.artefact_writer = self.artefact_manager.artefact_writer
        self.checklist_executor = self.quality_gate_manager.checklist_executor
        self.bmad_agents = self.agent_registry.bmad_agents
        self.crew = self.agent_registry.crew

        # Configure logging
        self._setup_logging()

    def _setup_logging(self):
        """Set up logging configuration."""
        log_config = self.config_manager._config["logging"]
        logging.basicConfig(
            level=getattr(logging, log_config["level"]), format=log_config["format"]
        )

    def get_api_client(self, provider: str) -> APIClient:
        """Get or create API client for a provider."""
        if provider not in self.api_clients:
            api_config = self.config_manager.get_api_config(provider)

            # Try to get API key from secure storage
            api_key = self.config_manager.get_api_key(provider)
            if api_key:
                api_config.api_key = api_key

            self.api_clients[provider] = APIClient(api_config)

        return self.api_clients[provider]

    async def make_api_request(
        self, provider: str, method: str, url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """Make API request with rate limiting and error handling."""
        try:
            # Check global rate limit
            api_config = self.config_manager.get_api_config(provider)
            self.rate_limiter.check_rate_limit(
                provider, api_config.rate_limit_requests, api_config.rate_limit_window
            )

            # Get client and make request
            client = self.get_api_client(provider)
            response = await getattr(client, method.lower())(url, **kwargs)

            # Record successful request
            self.rate_limiter.record_request(provider)

            return response

        except RateLimitError as e:
            self.logger.warning(f"Rate limit error for {provider}: {e}")
            # Set backoff if retry_after is provided
            if hasattr(e, "retry_after") and e.retry_after:
                self.rate_limiter.set_backoff(provider, e.retry_after)
            raise
        except APIError as e:
            self.logger.error(f"API error for {provider}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error for {provider}: {e}")
            raise APIError(f"Unexpected error: {str(e)}") from e

    # ===============================
    # Template Management
    # ===============================

    def load_bmad_templates(self) -> Dict[str, TemplateInfo]:
        """Load all BMAD templates from .bmad-core/templates/ directory.

        Returns:
            Dict[str, TemplateInfo]: Dictionary mapping template IDs to template info
        """
        return self.template_manager.load_templates()

    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        """Get a loaded template by ID.

        Args:
            template_id: Template identifier

        Returns:
            TemplateInfo or None: Template information if found
        """
        return self.template_manager.get_template(template_id)

    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all loaded templates with basic information.

        Returns:
            Dict[str, Dict[str, Any]]: Template summaries by ID
        """
        return self.template_manager.list_templates()

    def validate_template_dependencies(self, template_id: str) -> bool:
        """Validate that a template's dependencies are satisfied.

        Args:
            template_id: Template identifier to validate

        Returns:
            bool: True if dependencies are satisfied

        Raises:
            TemplateError: If dependencies are not satisfied
        """
        return self.template_manager.validate_template_dependencies(template_id)

    # ===============================
    # BMAD Agent Integration
    # ===============================

    def register_bmad_agents(self) -> bool:
        """Register all BMAD agents with CrewAI.

        Returns:
            bool: True if registration successful
        """
        return self.agent_registry.register_bmad_agents()

    def get_bmad_agent(self, agent_id: str):
        """Get a registered BMAD agent by ID.

        Args:
            agent_id: Agent identifier (e.g., 'scrum-master', 'dev-agent')

        Returns:
            Agent object or None if not found
        """
        return self.agent_registry.get_bmad_agent(agent_id)

    def list_bmad_agents(self):
        """List all registered BMAD agents.

        Returns:
            Dict of agent information
        """
        return self.agent_registry.list_bmad_agents()

    def test_agent_coordination(self):
        """Test agent coordination and crew functionality.

        Returns:
            Dict with coordination test results
        """
        return self.agent_registry.test_agent_coordination()

    # ===============================
    # Artefact Management
    # ===============================

    def write_artefact(self, artefact_type: str, content: str, **kwargs) -> bool:
        """Write artefact to BMAD folder structure.

        Args:
            artefact_type: Type of artefact ('prd', 'story', 'gate', 'assessment', 'epic')
            content: Artefact content
            **kwargs: Additional parameters for specific artefact types

        Returns:
            bool: True if successful
        """
        return self.artefact_manager.write_artefact(artefact_type, content, **kwargs)

    def test_artefact_generation(self) -> Dict[str, Any]:
        """Test artefact generation functionality.

        Returns:
            Dict with artefact generation test results
        """
        return self.artefact_manager.test_artefact_generation()

    # ===============================
    # Development Environment Testing
    # ===============================

    def test_development_environment(self):
        """Test development environment configuration and capabilities.

        Returns:
            Dict with environment test results
        """
        return self.development_tester.test_development_environment()

    # ===============================
    # Quality Gates & Checklists
    # ===============================

    def test_quality_gates(self):
        """Test quality gate and checklist execution framework.

        Returns:
            Dict with quality gate test results
        """
        return self.quality_gate_manager.test_quality_gates()

    def execute_checklist(
        self, checklist_id: str, context: Optional[Dict[str, Any]] = None
    ):
        """Execute a quality checklist.

        Args:
            checklist_id: ID of checklist to execute
            context: Optional context data for validation

        Returns:
            Dict with execution results
        """
        return self.quality_gate_manager.execute_checklist(checklist_id, context)

    def validate_gate(self, checklist_id: str, gate_type: str = "story"):
        """Validate a quality gate using a checklist.

        Args:
            checklist_id: Checklist to use for validation
            gate_type: Type of gate ('story', 'epic', 'sprint')

        Returns:
            Dict with gate validation results
        """
        return self.quality_gate_manager.validate_gate(checklist_id, gate_type)

    def list_available_checklists(self):
        """List all available checklists for quality gates.

        Returns:
            Dict with checklist information
        """
        return self.quality_gate_manager.list_available_checklists()

    def get_checklist_details(self, checklist_id: str):
        """Get detailed information about a specific checklist.

        Args:
            checklist_id: ID of checklist to retrieve

        Returns:
            Dict with checklist details or None if not found
        """
        return self.quality_gate_manager.get_checklist_details(checklist_id)

    async def close(self):
        """Close all API clients."""
        for client in self.api_clients.values():
            await client.close()
        self.api_clients.clear()

    @asynccontextmanager
    async def session(self):
        """Context manager for BMAD CrewAI session."""
        try:
            yield self
        finally:
            await self.close()
