"""Command-line interface for BMAD CrewAI."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import APIConfig, BMADConfig, ConfigManager
from .core import BmadCrewAI, RateLimitInfo
from .exceptions import BmadCrewAIError

logger = logging.getLogger(__name__)


class CLI:
    """Command-line interface for BMAD CrewAI."""

    def __init__(self):
        self.bmad = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.bmad = BmadCrewAI()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.bmad:
            await self.bmad.close()

    def run(self):
        """Run the CLI."""
        if len(sys.argv) < 2:
            self.print_help()
            return

        command = sys.argv[1]

        # Run async commands
        asyncio.run(self.run_async_command(command))

    async def run_async_command(self, command: str):
        """Run async command."""
        try:
            if command == "config":
                await self.handle_config()
            elif command == "test-api":
                await self.handle_test_api()
            elif command == "setup":
                await self.handle_setup()
            elif command == "status":
                await self.handle_status()
            else:
                print(f"Unknown command: {command}")
                self.print_help()

        except BmadCrewAIError as e:
            print(f"Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}")
            sys.exit(1)

    def print_help(self):
        """Print help information."""
        print("BMAD CrewAI CLI")
        print("================")
        print()
        print("Commands:")
        print("  setup     - Initial setup and configuration")
        print("  config    - Manage configuration and credentials")
        print("  test-api  - Test API connections with rate limiting")
        print("  status    - Show current configuration status")
        print()
        print("Examples:")
        print("  bmad-crewai setup")
        print("  bmad-crewai config set-api-key openai sk-your-key")
        print("  bmad-crewai test-api openai")
        print("  bmad-crewai status")

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
            import aiohttp
            import keyring

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
                        "Authorization": f"Bearer {cli.bmad.config_manager.get_api_key(provider)}"
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
                        print(
                            f"✅ Rate limit OK - {cli.bmad.rate_limiter._rate_limits.get(provider, RateLimitInfo()).requests_made} requests made"
                        )

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
            f"Config File: {'✅ Exists' if config_file.exists() else '❌ Not found'} ({config_file})"
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
            "2. Run 'bmad-crewai config set-api-key <provider> <key>' to add API keys"
        )
        print("3. Run 'bmad-crewai test-api <provider>' to test connections")


def main():
    """Main CLI entry point."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
