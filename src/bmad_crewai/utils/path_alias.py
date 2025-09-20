"""Path alias resolver utility for BMAD artefact management.

This module provides a lightweight utility for resolving legacy BMAD file names
to their canonical paths, ensuring stability across documentation changes.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PathAliasResolver:
    """Resolves legacy BMAD file paths to canonical paths.

    This utility maintains a configurable mapping of alias paths to canonical paths,
    ensuring that links and references remain stable when documentation is reorganized.
    """

    def __init__(self, alias_map: Optional[Dict[str, str]] = None):
        """Initialize the path alias resolver.

        Args:
            alias_map: Optional custom alias mapping. If None, uses default BMAD aliases.
        """
        # Default BMAD alias mappings for legacy file names
        self._alias_map = alias_map or {
            "docs/brownfield-prd.md": "docs/prd.md",
            "docs/brownfield-architecture.md": "docs/architecture.md",
        }

        logger.info(
            f"PathAliasResolver initialized with {len(self._alias_map)} aliases"
        )

    def resolve_path(self, path: str) -> str:
        """Resolve a path to its canonical form if it's a known alias.

        Args:
            path: The path to resolve

        Returns:
            str: The canonical path if path is an alias, otherwise the original path
        """
        if path in self._alias_map:
            canonical_path = self._alias_map[path]
            logger.debug(f"Resolved alias '{path}' to canonical '{canonical_path}'")
            return canonical_path

        return path

    def is_alias(self, path: str) -> bool:
        """Check if a path is a known alias.

        Args:
            path: The path to check

        Returns:
            bool: True if the path is a known alias, False otherwise
        """
        return path in self._alias_map

    def add_alias(self, alias: str, canonical: str) -> None:
        """Add a new alias mapping.

        Args:
            alias: The alias path
            canonical: The canonical path
        """
        self._alias_map[alias] = canonical
        logger.info(f"Added alias mapping: '{alias}' -> '{canonical}'")

    def get_alias_map(self) -> Dict[str, str]:
        """Get a copy of the current alias mapping.

        Returns:
            Dict[str, str]: Copy of the alias mapping
        """
        return self._alias_map.copy()

    def get_migration_guidance(self, alias: str) -> Optional[str]:
        """Get migration guidance for a resolved alias.

        Args:
            alias: The alias path

        Returns:
            Optional[str]: Migration guidance message if alias resolves to missing canonical
        """
        if self.is_alias(alias):
            canonical = self._alias_map[alias]
            return f"Migration needed: '{alias}' should be updated to '{canonical}'"
        return None


# Global resolver instance for easy access
_resolver = PathAliasResolver()


def resolve_path(path: str) -> str:
    """Global function to resolve a path to its canonical form.

    Args:
        path: The path to resolve

    Returns:
        str: The canonical path if path is an alias, otherwise the original path
    """
    return _resolver.resolve_path(path)


def is_alias(path: str) -> bool:
    """Global function to check if a path is a known alias.

    Args:
        path: The path to check

    Returns:
        bool: True if the path is a known alias, False otherwise
    """
    return _resolver.is_alias(path)


def get_migration_guidance(alias: str) -> Optional[str]:
    """Global function to get migration guidance for an alias.

    Args:
        alias: The alias path

    Returns:
        Optional[str]: Migration guidance message if applicable
    """
    return _resolver.get_migration_guidance(alias)
