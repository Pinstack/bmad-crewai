"""BMAD CrewAI Integration Package.

This package provides a structured integration between CrewAI's multi-agent
orchestration capabilities and the BMAD-Method framework.

Architecture:
- CrewAI acts as the primary orchestration engine
- Reads BMAD YAML templates from .bmad-core/templates/
- Coordinates specialized BMAD agents (PM, Architect, QA, Dev, PO, SM)
- Writes all artefacts to BMAD folder structure (docs/, stories/, qa/, etc.)
- Maintains BMAD methodology execution flow and quality gates

Security Features:
- Secure credential storage (keyring + encrypted files)
- API rate limiting with exponential backoff
- Comprehensive error handling and retry mechanisms
"""

__version__ = "0.1.0"
__author__ = "Raedmund"
__email__ = "raedmund@example.com"

import os as _os  # import guard helper

# Minimal-by-default imports to avoid optional dependency issues during tooling
if _os.environ.get("BMAD_MIN_IMPORTS", "1") == "1":  # default minimal
    AgentRegistry = None  # type: ignore
    APIClient = None  # type: ignore
    RateLimiter = None  # type: ignore
    ArtefactManager = None  # type: ignore
    BMADArtefactWriter = None  # type: ignore
    ChecklistExecutor = None  # type: ignore
    CLI = None  # type: ignore
    main = None  # type: ignore
    APIConfig = None  # type: ignore
    BMADConfig = None  # type: ignore
    ConfigManager = None  # type: ignore
    CredentialStore = None  # type: ignore
    BmadCrewAI = None  # type: ignore
    DevelopmentTester = None  # type: ignore
    AgentError = APIError = AuthenticationError = BmadCrewAIError = ConfigurationError = CredentialError = RateLimitError = TemplateError = ValidationError = WorkflowError = None  # type: ignore
    QualityGateManager = None  # type: ignore
    TemplateInfo = None  # type: ignore
    TemplateManager = None  # type: ignore
else:
    try:  # pragma: no cover
        from .agent_registry import AgentRegistry
        from .api_client import APIClient, RateLimiter
        from .artefact_manager import ArtefactManager
        from .artefact_writer import BMADArtefactWriter
        from .checklist_executor import ChecklistExecutor
        from .cli import CLI, main
        from .config import APIConfig, BMADConfig, ConfigManager, CredentialStore
        from .core import BmadCrewAI
        from .development_tester import DevelopmentTester
        from .exceptions import (
            AgentError,
            APIError,
            AuthenticationError,
            BmadCrewAIError,
            ConfigurationError,
            CredentialError,
            RateLimitError,
            TemplateError,
            ValidationError,
            WorkflowError,
        )
        from .quality_gate_manager import QualityGateManager
        from .template_manager import TemplateInfo, TemplateManager
    except Exception:  # pragma: no cover
        # Fallback to minimal if full import fails
        AgentRegistry = None  # type: ignore
        APIClient = None  # type: ignore
        RateLimiter = None  # type: ignore
        ArtefactManager = None  # type: ignore
        BMADArtefactWriter = None  # type: ignore
        ChecklistExecutor = None  # type: ignore
        CLI = None  # type: ignore
        main = None  # type: ignore
        APIConfig = None  # type: ignore
        BMADConfig = None  # type: ignore
        ConfigManager = None  # type: ignore
        CredentialStore = None  # type: ignore
        BmadCrewAI = None  # type: ignore
        DevelopmentTester = None  # type: ignore
        AgentError = APIError = AuthenticationError = BmadCrewAIError = ConfigurationError = CredentialError = RateLimitError = TemplateError = ValidationError = WorkflowError = None  # type: ignore
        QualityGateManager = None  # type: ignore
        TemplateInfo = None  # type: ignore
        TemplateManager = None  # type: ignore

__all__ = [
    # Core classes
    "BmadCrewAI",
    "APIClient",
    "RateLimiter",
    "TemplateInfo",
    # Managers
    "AgentRegistry",
    "ArtefactManager",
    "DevelopmentTester",
    "QualityGateManager",
    "TemplateManager",
    # Artefact and checklist components
    "BMADArtefactWriter",
    "ChecklistExecutor",
    # Configuration
    "ConfigManager",
    "CredentialStore",
    "APIConfig",
    "BMADConfig",
    # Exceptions
    "BmadCrewAIError",
    "ConfigurationError",
    "CredentialError",
    "APIError",
    "RateLimitError",
    "AuthenticationError",
    "ValidationError",
    "TemplateError",
    "AgentError",
    "WorkflowError",
    # CLI
    "CLI",
    "main",
]
