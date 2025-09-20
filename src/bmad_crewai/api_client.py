"""API client with rate limiting and error handling."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

import aiohttp
from aiohttp import ClientError, ClientTimeout

from .config import APIConfig
from .exceptions import APIError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limiting information for an API."""

    requests_made: int = 0
    window_start: float = field(default_factory=time.time)
    backoff_until: Optional[float] = None


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
                f"Rate limit backoff active. Retry after "
                f"{self.rate_limit_info.backoff_until - now:.1f} seconds"
            )

        # Check request limit
        if self.rate_limit_info.requests_made >= self.config.rate_limit_requests:
            raise RateLimitError(
                f"Rate limit exceeded: "
                f"{self.rate_limit_info.requests_made}/"
                f"{self.config.rate_limit_requests} "
                f"requests in {self.config.rate_limit_window}s window"
            )

    def _update_rate_limit(self, response: aiohttp.ClientResponse) -> None:
        """Update rate limiting info based on response headers."""
        self.rate_limit_info.requests_made += 1

        # Check for rate limit headers
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            # Retry-After may be seconds or an HTTP-date
            seconds = self._parse_retry_after(retry_after)
            if seconds is not None:
                self.rate_limit_info.backoff_until = time.time() + seconds
                logger.warning(f"Rate limit hit. Backing off for {seconds} seconds")

        # Check for common rate limit status codes
        if response.status == 429:
            retry_after = response.headers.get("Retry-After", "60")
            seconds = self._parse_retry_after(retry_after)
            self.rate_limit_info.backoff_until = time.time() + (
                seconds if seconds is not None else 60
            )
            logger.warning(
                f"Rate limit exceeded (429). Backing off for {seconds if seconds is not None else 60} seconds"
            )

    def _parse_retry_after(self, value: str) -> Optional[int]:
        """Parse Retry-After header supporting seconds or HTTP-date.

        Returns number of seconds to wait, or None if parsing fails.
        """
        try:
            # Try integer seconds first
            return int(value)
        except Exception:
            pass
        try:
            # HTTP-date format
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(value)
            if dt is None:
                return None
            now = time.time()
            wait = dt.timestamp() - now
            return max(0, int(wait))
        except Exception:
            return None

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
                            ra_seconds = self._parse_retry_after(retry_after)
                            raise RateLimitError(
                                f"Rate limit exceeded: {await response.text()}",
                                status_code=response.status,
                                retry_after=ra_seconds,
                            )
                        elif response.status >= 500:
                            # Server error - retry
                            raise APIError(
                                f"Server error {response.status}: "
                                f"{await response.text()}",
                                status_code=response.status,
                            )
                        else:
                            # Client error - don't retry
                            raise APIError(
                                f"Client error {response.status}: "
                                f"{await response.text()}",
                                status_code=response.status,
                            )

                    return response

            except (ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}): {e}. "
                        f"Retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Request failed after {self.config.max_retries + 1} "
                        f"attempts: {e}"
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
                f"{info.requests_made}/{requests_per_window} "
                f"requests in {window_seconds}s window"
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
