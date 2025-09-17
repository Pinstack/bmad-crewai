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

from .cli import CLI, main
from .config import APIConfig, BMADConfig, ConfigManager, CredentialStore
from .core import APIClient, BmadCrewAI, RateLimiter, TemplateInfo
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

__all__ = [
    # Core classes
    "BmadCrewAI",
    "APIClient",
    "RateLimiter",
    "TemplateInfo",
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
