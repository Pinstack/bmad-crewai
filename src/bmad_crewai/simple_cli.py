"""Simple CLI for BMAD CrewAI MVP."""

import asyncio
import sys

from .simple_api import BMADCrewAISimple
from .simple_config import SimpleConfig


def main():
    """Simple CLI entry point."""
    if len(sys.argv) < 2:
        print("BMAD CrewAI MVP")
        print("================")
        print()
        print("Commands:")
        print("  setup     - Configure API keys")
        print("  test      - Test API connection")
        print("  status    - Show current status")
        return

    command = sys.argv[1]

    if command == "setup":
        setup()
    elif command == "test":
        asyncio.run(test_api())
    elif command == "status":
        show_status()
    else:
        print(f"Unknown command: {command}")


def setup():
    """Simple setup - just ask for API keys."""
    print("BMAD CrewAI Setup")
    print("==================")

    config = SimpleConfig()

    providers = ["openai", "anthropic"]
    for provider in providers:
        current_key = config.get_api_key(provider)
        if current_key:
            masked = current_key[:8] + "*" * (len(current_key) - 16) + current_key[-8:]
            print(f"✅ {provider.upper()} API key configured: {masked}")
        else:
            key = input(
                f"Enter {provider.upper()} API key (or press Enter to skip): "
            ).strip()
            if key:
                config.save_api_key(provider, key)
                print(f"✅ {provider.upper()} API key saved")
            else:
                print(f"❌ {provider.upper()} API key not configured")


async def test_api():
    """Test API connections."""
    print("Testing API connections...")
    print("==========================")

    bmad = BMADCrewAISimple()

    try:
        providers = ["openai", "anthropic"]
        for provider in providers:
            if bmad.config.get_api_key(provider):
                print(f"\nTesting {provider.upper()}...")
                try:
                    client = bmad.get_api_client(provider)

                    async with client:
                        if provider == "openai":
                            result = await client.make_request(
                                "GET", "https://api.openai.com/v1/models"
                            )
                            print(f"✅ {provider.upper()} API working")
                        elif provider == "anthropic":
                            # Simple test request
                            print(
                                f"✅ {provider.upper()} API configured (test skipped for MVP)"
                            )
                        else:
                            print(f"❌ Unknown provider: {provider}")

                except Exception as e:
                    print(f"❌ {provider.upper()} API test failed: {e}")
            else:
                print(f"❌ {provider.upper()} API key not configured")

    finally:
        await bmad.close()


def show_status():
    """Show current status."""
    print("BMAD CrewAI Status")
    print("==================")

    config = SimpleConfig()

    # Check BMAD core
    from pathlib import Path

    bmad_core = Path(".bmad-core")
    print(f"BMAD Core: {'✅ Found' if bmad_core.exists() else '❌ Not found'}")

    # Check API keys
    providers = ["openai", "anthropic"]
    for provider in providers:
        key = config.get_api_key(provider)
        if key:
            masked = key[:8] + "*" * (len(key) - 16) + key[-8:]
            print(f"{provider.upper()} API: ✅ Configured ({masked})")
        else:
            print(f"{provider.upper()} API: ❌ Not configured")

    print("\nTo configure:")
    print("1. Run 'python -m bmad_crewai.simple_cli setup'")
    print("2. Run 'python -m bmad_crewai.simple_cli test'")


if __name__ == "__main__":
    main()
