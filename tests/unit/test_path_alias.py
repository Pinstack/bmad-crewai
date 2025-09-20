"""Unit tests for path alias resolver utility."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from bmad_crewai.utils.path_alias import (
    PathAliasResolver,
    get_migration_guidance,
    is_alias,
    resolve_path,
)


class TestPathAliasResolver(unittest.TestCase):
    """Test cases for PathAliasResolver class."""

    def setUp(self):
        """Set up test fixtures."""
        self.resolver = PathAliasResolver(
            {
                "docs/brownfield-prd.md": "docs/prd.md",
                "docs/brownfield-architecture.md": "docs/architecture.md",
            }
        )

    def test_resolve_path_canonical_no_change(self):
        """Test that canonical paths are returned unchanged."""
        canonical_path = "docs/prd.md"
        result = self.resolver.resolve_path(canonical_path)
        self.assertEqual(result, canonical_path)

    def test_resolve_path_known_alias(self):
        """Test that known aliases resolve to canonical paths."""
        alias_path = "docs/brownfield-prd.md"
        expected = "docs/prd.md"
        result = self.resolver.resolve_path(alias_path)
        self.assertEqual(result, expected)

    def test_resolve_path_unknown_path_unchanged(self):
        """Test that unknown paths are returned unchanged."""
        unknown_path = "docs/some-other-file.md"
        result = self.resolver.resolve_path(unknown_path)
        self.assertEqual(result, unknown_path)

    def test_is_alias_known_alias(self):
        """Test that known aliases return True."""
        alias_path = "docs/brownfield-prd.md"
        result = self.resolver.is_alias(alias_path)
        self.assertTrue(result)

    def test_is_alias_canonical_path(self):
        """Test that canonical paths return False."""
        canonical_path = "docs/prd.md"
        result = self.resolver.is_alias(canonical_path)
        self.assertFalse(result)

    def test_is_alias_unknown_path(self):
        """Test that unknown paths return False."""
        unknown_path = "docs/unknown-file.md"
        result = self.resolver.is_alias(unknown_path)
        self.assertFalse(result)

    def test_get_migration_guidance_known_alias(self):
        """Test migration guidance for known aliases."""
        alias_path = "docs/brownfield-prd.md"
        expected = "Migration needed: 'docs/brownfield-prd.md' should be updated to 'docs/prd.md'"
        result = self.resolver.get_migration_guidance(alias_path)
        self.assertEqual(result, expected)

    def test_get_migration_guidance_unknown_path(self):
        """Test migration guidance for unknown paths returns None."""
        unknown_path = "docs/unknown-file.md"
        result = self.resolver.get_migration_guidance(unknown_path)
        self.assertIsNone(result)

    def test_add_alias(self):
        """Test adding a new alias mapping."""
        new_alias = "docs/old-name.md"
        canonical = "docs/new-name.md"

        self.resolver.add_alias(new_alias, canonical)

        # Verify the alias was added
        self.assertTrue(self.resolver.is_alias(new_alias))
        self.assertEqual(self.resolver.resolve_path(new_alias), canonical)

    def test_get_alias_map_returns_copy(self):
        """Test that get_alias_map returns a copy, not the original."""
        original_map = self.resolver.get_alias_map()
        original_map["new_key"] = "new_value"

        # Original resolver should not be modified
        self.assertNotIn("new_key", self.resolver.get_alias_map())


class TestGlobalFunctions(unittest.TestCase):
    """Test cases for global utility functions."""

    def test_resolve_path_global_function(self):
        """Test global resolve_path function."""
        # Test with known alias
        result = resolve_path("docs/brownfield-prd.md")
        self.assertEqual(result, "docs/prd.md")

        # Test with canonical path
        result = resolve_path("docs/prd.md")
        self.assertEqual(result, "docs/prd.md")

        # Test with unknown path
        result = resolve_path("docs/unknown.md")
        self.assertEqual(result, "docs/unknown.md")

    def test_is_alias_global_function(self):
        """Test global is_alias function."""
        # Test with known alias
        self.assertTrue(is_alias("docs/brownfield-prd.md"))

        # Test with canonical path
        self.assertFalse(is_alias("docs/prd.md"))

        # Test with unknown path
        self.assertFalse(is_alias("docs/unknown.md"))

    def test_get_migration_guidance_global_function(self):
        """Test global get_migration_guidance function."""
        # Test with known alias
        result = get_migration_guidance("docs/brownfield-prd.md")
        expected = "Migration needed: 'docs/brownfield-prd.md' should be updated to 'docs/prd.md'"
        self.assertEqual(result, expected)

        # Test with unknown path
        self.assertIsNone(get_migration_guidance("docs/unknown.md"))


class TestLinkValidationIntegration(unittest.TestCase):
    """Test cases for link validation integration."""

    def setUp(self):
        """Set up test fixtures with temporary files."""
        self.temp_dir = tempfile.mkdtemp()
        self.canonical_file = os.path.join(self.temp_dir, "prd.md")
        self.alias_path = "docs/brownfield-prd.md"

        # Create the canonical file
        with open(self.canonical_file, "w") as f:
            f.write("# Test PRD\n\nSome content.")

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_link_validation_with_alias_resolution(self):
        """Test that link validation works correctly with alias resolution."""
        from bmad_crewai.quality_gate_manager import QualityGateManager

        # Create a content string with an alias link
        content = f"""
        # Test Document

        This is a test document with a link to [{self.alias_path}]({self.alias_path}).
        """

        # Create quality gate manager
        qgm = QualityGateManager()

        # Mock the canonical file existence check
        with patch("os.path.exists") as mock_exists:
            # Mock that the canonical file exists
            mock_exists.return_value = True

            # Test the validation
            results = qgm._validate_internal_references(content)

            # Verify that the alias was resolved in cross_references
            cross_refs = results.get("cross_references", [])
            self.assertTrue(any("resolved to" in ref for ref in cross_refs))

            # Verify no consistency issues (since canonical exists)
            consistency_issues = results.get("consistency_issues", [])
            self.assertEqual(len(consistency_issues), 0)

    def test_link_validation_with_missing_canonical(self):
        """Test that link validation provides migration guidance for missing canonicals."""
        from bmad_crewai.quality_gate_manager import QualityGateManager

        # Create a content string with an alias link
        content = f"""
        # Test Document

        This is a test document with a link to [{self.alias_path}]({self.alias_path}).
        """

        # Create quality gate manager
        qgm = QualityGateManager()

        # Mock the canonical file as missing
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False

            # Test the validation
            results = qgm._validate_internal_references(content)

            # Verify migration guidance is provided
            consistency_issues = results.get("consistency_issues", [])
            self.assertTrue(
                any("Migration needed" in issue for issue in consistency_issues)
            )


if __name__ == "__main__":
    unittest.main()
