"""Custom exceptions for BMAD CrewAI."""


class BmadCrewAIError(Exception):
    """Base exception for BMAD CrewAI errors."""

    pass


class ConfigurationError(BmadCrewAIError):
    """Raised when there's a configuration error."""

    pass


class CredentialError(BmadCrewAIError):
    """Raised when there's a credential-related error."""

    pass


class APIError(BmadCrewAIError):
    """Raised when there's an API-related error."""

    def __init__(self, message: str, status_code: int = None, retry_after: int = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""

    pass


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    pass


class ValidationError(BmadCrewAIError):
    """Raised when validation fails."""

    pass


class TemplateError(BmadCrewAIError):
    """Raised when there's an error with BMAD templates."""

    pass


class AgentError(BmadCrewAIError):
    """Raised when there's an error with BMAD agents."""

    pass


class WorkflowError(BmadCrewAIError):
    """Raised when there's an error in workflow execution."""

    pass
