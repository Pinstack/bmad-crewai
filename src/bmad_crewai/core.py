"""Core BMAD CrewAI integration with rate limiting and error handling."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

import aiohttp
import yaml
from aiohttp import ClientError, ClientTimeout

from .config import APIConfig, ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limiting information for an API."""

    requests_made: int = 0
    window_start: float = field(default_factory=time.time)
    backoff_until: Optional[float] = None


class APIError(Exception):
    """Base exception for API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class RateLimitError(APIError):
    """Exception raised when rate limit is exceeded."""

    pass


@dataclass
class TemplateInfo:
    """Information about a loaded BMAD template."""

    id: str
    name: str
    version: str
    template_path: Path
    workflow_mode: str
    sections: Dict[str, Any]
    agent_config: Dict[str, Any]


class TemplateError(Exception):
    """Exception raised when template loading or validation fails."""

    pass


class APIClient:
    """HTTP client with rate limiting and error handling."""

    def __init__(
        self, config: APIConfig, session: Optional[aiohttp.ClientSession] = None
    ):
        self.config = config
        self.session = session or aiohttp.ClientSession(
            timeout=ClientTimeout(total=config.timeout)
        )
        self.rate_limit_info = RateLimitInfo()
        self._closed = False

    async def close(self):
        """Close the HTTP session."""
        if not self._closed and self.session:
            await self.session.close()
            self._closed = True

    def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        now = time.time()

        # Reset window if needed
        if now - self.rate_limit_info.window_start >= self.config.rate_limit_window:
            self.rate_limit_info.requests_made = 0
            self.rate_limit_info.window_start = now

        # Check if we're currently backing off
        if (
            self.rate_limit_info.backoff_until
            and now < self.rate_limit_info.backoff_until
        ):
            raise RateLimitError(
                f"Rate limit backoff active. Retry after {self.rate_limit_info.backoff_until - now:.1f} seconds"
            )

        # Check request limit
        if self.rate_limit_info.requests_made >= self.config.rate_limit_requests:
            raise RateLimitError(
                f"Rate limit exceeded: {self.rate_limit_info.requests_made}/{self.config.rate_limit_requests} "
                f"requests in {self.config.rate_limit_window}s window"
            )

    def _update_rate_limit(self, response: aiohttp.ClientResponse) -> None:
        """Update rate limiting info based on response headers."""
        self.rate_limit_info.requests_made += 1

        # Check for rate limit headers
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                self.rate_limit_info.backoff_until = time.time() + int(retry_after)
                logger.warning(f"Rate limit hit. Backing off for {retry_after} seconds")
            except ValueError:
                pass

        # Check for common rate limit status codes
        if response.status == 429:
            retry_after = response.headers.get("Retry-After", "60")
            try:
                self.rate_limit_info.backoff_until = time.time() + int(retry_after)
                logger.warning(
                    f"Rate limit exceeded (429). Backing off for {retry_after} seconds"
                )
            except ValueError:
                self.rate_limit_info.backoff_until = time.time() + 60

    async def _make_request_with_retry(
        self, method: str, url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with retry logic."""
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                self._check_rate_limit()

                logger.debug(
                    f"Making {method} request to {url} (attempt {attempt + 1})"
                )

                async with self.session.request(method, url, **kwargs) as response:
                    self._update_rate_limit(response)

                    if response.status >= 400:
                        if response.status == 429:
                            retry_after = response.headers.get("Retry-After", "60")
                            raise RateLimitError(
                                f"Rate limit exceeded: {await response.text()}",
                                status_code=response.status,
                                retry_after=(
                                    int(retry_after) if retry_after.isdigit() else None
                                ),
                            )
                        elif response.status >= 500:
                            # Server error - retry
                            raise APIError(
                                f"Server error {response.status}: {await response.text()}",
                                status_code=response.status,
                            )
                        else:
                            # Client error - don't retry
                            raise APIError(
                                f"Client error {response.status}: {await response.text()}",
                                status_code=response.status,
                            )

                    return response

            except (ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}): {e}. Retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Request failed after {self.config.max_retries + 1} attempts: {e}"
                    )
                    raise APIError(f"Request failed after retries: {str(e)}") from e
            except RateLimitError:
                # Don't retry rate limit errors immediately
                raise
            except APIError:
                # Don't retry client errors
                raise

        raise APIError(f"All retry attempts failed. Last error: {str(last_exception)}")

    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make GET request."""
        return await self._make_request_with_retry("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make POST request."""
        return await self._make_request_with_retry("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make PUT request."""
        return await self._make_request_with_retry("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make DELETE request."""
        return await self._make_request_with_retry("DELETE", url, **kwargs)


class RateLimiter:
    """Global rate limiter for managing multiple API clients."""

    def __init__(self):
        self._rate_limits: Dict[str, RateLimitInfo] = {}

    def check_rate_limit(
        self, provider: str, requests_per_window: int, window_seconds: int
    ) -> None:
        """Check if rate limit allows the request."""
        if provider not in self._rate_limits:
            self._rate_limits[provider] = RateLimitInfo()

        info = self._rate_limits[provider]
        now = time.time()

        # Reset window if needed
        if now - info.window_start >= window_seconds:
            info.requests_made = 0
            info.window_start = now

        # Check backoff
        if info.backoff_until and now < info.backoff_until:
            raise RateLimitError(
                f"Rate limit backoff active for {provider}. "
                f"Retry after {info.backoff_until - now:.1f} seconds"
            )

        # Check request limit
        if info.requests_made >= requests_per_window:
            raise RateLimitError(
                f"Rate limit exceeded for {provider}: "
                f"{info.requests_made}/{requests_per_window} requests in {window_seconds}s window"
            )

    def record_request(self, provider: str) -> None:
        """Record a successful request."""
        if provider in self._rate_limits:
            self._rate_limits[provider].requests_made += 1

    def set_backoff(self, provider: str, seconds: int) -> None:
        """Set backoff period for a provider."""
        if provider not in self._rate_limits:
            self._rate_limits[provider] = RateLimitInfo()

        self._rate_limits[provider].backoff_until = time.time() + seconds


class BmadCrewAI:
    """Main BMAD CrewAI integration class."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_manager = ConfigManager(config_file)
        self.rate_limiter = RateLimiter()
        self.api_clients: Dict[str, APIClient] = {}
        self.templates: Dict[str, TemplateInfo] = {}
        self.logger = logging.getLogger(__name__)

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

    def load_bmad_templates(self) -> Dict[str, TemplateInfo]:
        """Load all BMAD templates from .bmad-core/templates/ directory.

        Returns:
            Dict[str, TemplateInfo]: Dictionary mapping template IDs to template info

        Raises:
            TemplateError: If template loading or validation fails
        """
        templates_dir = Path(".bmad-core/templates")
        if not templates_dir.exists():
            raise TemplateError(f"BMAD templates directory not found: {templates_dir}")

        self.logger.info(f"Loading BMAD templates from {templates_dir}")

        for template_file in templates_dir.glob("*.yaml"):
            try:
                template_info = self._load_single_template(template_file)
                self.templates[template_info.id] = template_info
                self.logger.debug(f"Loaded template: {template_info.id} ({template_info.name})")
            except Exception as e:
                self.logger.error(f"Failed to load template {template_file}: {e}")
                raise TemplateError(f"Template loading failed for {template_file}: {e}") from e

        self.logger.info(f"Successfully loaded {len(self.templates)} BMAD templates")
        return self.templates

    def _load_single_template(self, template_path: Path) -> TemplateInfo:
        """Load and validate a single BMAD template.

        Args:
            template_path: Path to the YAML template file

        Returns:
            TemplateInfo: Parsed and validated template information

        Raises:
            TemplateError: If template validation fails
        """
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise TemplateError(f"Invalid YAML syntax in {template_path}: {e}") from e
        except FileNotFoundError:
            raise TemplateError(f"Template file not found: {template_path}")

        # Validate required fields
        if not isinstance(template_data, dict):
            raise TemplateError(f"Template must be a dictionary: {template_path}")

        template_meta = template_data.get('template', {})
        workflow = template_data.get('workflow', {})
        sections = template_data.get('sections', [])
        agent_config = template_data.get('agent_config', {})

        # Validate required template metadata
        required_fields = ['id', 'name', 'version']
        for field in required_fields:
            if field not in template_meta:
                raise TemplateError(f"Missing required field '{field}' in template {template_path}")

        # Validate template ID format
        template_id = template_meta['id']
        if not isinstance(template_id, str) or not template_id.strip():
            raise TemplateError(f"Invalid template ID: {template_id}")

        # Extract workflow mode
        workflow_mode = workflow.get('mode', 'interactive')
        if workflow_mode not in ['interactive', 'batch', 'automated']:
            self.logger.warning(f"Unknown workflow mode '{workflow_mode}' in {template_path}, defaulting to 'interactive'")
            workflow_mode = 'interactive'

        # Validate sections structure
        if not isinstance(sections, list):
            raise TemplateError(f"Sections must be a list in template {template_path}")

        # Convert sections list to dictionary by ID for easier access
        sections_dict = {}
        for section in sections:
            if not isinstance(section, dict) or 'id' not in section:
                raise TemplateError(f"Invalid section format in template {template_path}")
            sections_dict[section['id']] = section

        # Extract agent assignments and validate
        editable_sections = agent_config.get('editable_sections', [])
        if not isinstance(editable_sections, list):
            raise TemplateError(f"editable_sections must be a list in template {template_path}")

        # Validate agent ownership in sections
        for section_id, section in sections_dict.items():
            if 'owner' not in section:
                self.logger.warning(f"Section '{section_id}' missing owner in {template_path}")
            if 'editors' in section and not isinstance(section['editors'], list):
                raise TemplateError(f"editors must be a list for section '{section_id}' in {template_path}")

        return TemplateInfo(
            id=template_meta['id'],
            name=template_meta['name'],
            version=template_meta['version'],
            template_path=template_path,
            workflow_mode=workflow_mode,
            sections=sections_dict,
            agent_config=agent_config
        )

    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        """Get a loaded template by ID.

        Args:
            template_id: Template identifier

        Returns:
            TemplateInfo or None: Template information if found
        """
        return self.templates.get(template_id)

    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all loaded templates with basic information.

        Returns:
            Dict[str, Dict[str, Any]]: Template summaries by ID
        """
        return {
            template_id: {
                'name': info.name,
                'version': info.version,
                'workflow_mode': info.workflow_mode,
                'sections_count': len(info.sections)
            }
            for template_id, info in self.templates.items()
        }

    def validate_template_dependencies(self, template_id: str) -> bool:
        """Validate that a template's dependencies are satisfied.

        Args:
            template_id: Template identifier to validate

        Returns:
            bool: True if dependencies are satisfied

        Raises:
            TemplateError: If dependencies are not satisfied
        """
        template = self.get_template(template_id)
        if not template:
            raise TemplateError(f"Template not found: {template_id}")

        # Check for required agent configurations
        required_agents = ['scrum-master', 'product-owner', 'dev-agent', 'qa-agent', 'product-manager', 'architect']
        available_agents = []  # In future, this could check actual agent availability

        # For now, just log warnings about agent dependencies
        for section_id, section in template.sections.items():
            owner = section.get('owner')
            if owner and owner not in required_agents:
                self.logger.warning(f"Unknown agent '{owner}' required for section '{section_id}' in template {template_id}")

        # Check for template-specific dependencies
        workflow = template.workflow_mode
        if workflow == 'automated' and not template.agent_config.get('allow_automated', False):
            raise TemplateError(f"Template {template_id} has automated workflow but doesn't allow automated execution")

        return True

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
