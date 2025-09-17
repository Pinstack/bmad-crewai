"""Core BMAD CrewAI integration with rate limiting and error handling."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional

import aiohttp
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
