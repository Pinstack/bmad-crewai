"""Simple API client with basic rate limiting for BMAD CrewAI MVP."""

import asyncio
import time
from typing import Optional

import aiohttp

from .simple_config import SimpleConfig


class SimpleAPIClient:
    """Simple API client with basic rate limiting."""

    def __init__(self, provider: str, config: SimpleConfig):
        self.provider = provider
        self.config = config
        self.last_request = 0
        self.min_delay = 1.0  # 1 second between requests
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _wait_for_rate_limit(self):
        """Simple rate limiting - wait if needed."""
        now = time.time()
        time_since_last = now - self.last_request
        if time_since_last < self.min_delay:
            await asyncio.sleep(self.min_delay - time_since_last)
        self.last_request = time.time()

    async def make_request(self, method: str, url: str, **kwargs) -> dict:
        """Make API request with basic error handling.

        Robustness additions:
        - Handle HTTP 204 (no content) by returning an empty dict
        - If Content-Type is not JSON, return a dict with status/text
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        await self._wait_for_rate_limit()

        try:
            api_key = self.config.get_api_key(self.provider)
            if api_key:
                headers = kwargs.get("headers", {})
                if self.provider == "openai":
                    headers["Authorization"] = f"Bearer {api_key}"
                elif self.provider == "anthropic":
                    headers["x-api-key"] = api_key
                kwargs["headers"] = headers

            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 429:  # Rate limit
                    await asyncio.sleep(5)  # Simple backoff
                    return await self.make_request(method, url, **kwargs)  # Retry once

                response.raise_for_status()

                # 204 No Content
                if response.status == 204:
                    return {}

                # Prefer JSON if available
                ctype = response.headers.get("Content-Type", "").lower()
                if "application/json" in ctype or "+json" in ctype:
                    return await response.json()
                else:
                    text = await response.text()
                    return {"status": response.status, "text": text}

        except aiohttp.ClientError as e:
            raise Exception(f"API request failed: {e}") from e
        except Exception as e:
            raise Exception(f"Unexpected error: {e}") from e


class BMADCrewAISimple:
    """Simplified BMAD CrewAI for MVP."""

    def __init__(self):
        self.config = SimpleConfig()
        self.api_clients = {}

    def get_api_client(self, provider: str) -> SimpleAPIClient:
        """Get or create API client."""
        if provider not in self.api_clients:
            self.api_clients[provider] = SimpleAPIClient(provider, self.config)
        return self.api_clients[provider]

    async def close(self):
        """Close all clients."""
        for client in self.api_clients.values():
            if client.session:
                await client.session.close()
        self.api_clients.clear()
