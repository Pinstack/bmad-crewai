"""Tests for BMADArtefactWriter functionality."""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from src.bmad_crewai.artefact_writer import BMADArtefactWriter


class TestBMADArtefactWriter:
    """Test suite for BMADArtefactWriter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.writer = BMADArtefactWriter(base_path=str(self.temp_dir))

    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove temp directory and all contents
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_filder_mapping_exists(self):
        """Test that FOLDER_MAPPING is properly defined."""
        assert hasattr(self.writer, "FOLDER_MAPPING")
        assert isinstance(self.writer.FOLDER_MAPPING, dict)
        assert "prd" in self.writer.FOLDER_MAPPING
        assert "stories" in self.writer.FOLDER_MAPPING
        assert "qa_assessments" in self.writer.FOLDER_MAPPING
        assert "qa_gates" in self.writer.FOLDER_MAPPING

    def test_validate_folder_structure_creates_directories(self):
        """Test that validate_folder_structure creates required directories."""
        # Ensure directories don't exist initially
        docs_path = self.temp_dir / "docs"
        stories_path = docs_path / "stories"
        qa_path = docs_path / "qa"
        qa_gates_path = qa_path / "gates"
        qa_assessments_path = qa_path / "assessments"

        assert not docs_path.exists()
        assert not stories_path.exists()
        assert not qa_gates_path.exists()
        assert not qa_assessments_path.exists()

        # Call validate_folder_structure
        result = self.writer.validate_folder_structure()

        # Verify result and directory creation
        assert result is True
        assert docs_path.exists()
        assert docs_path.is_dir()
        assert stories_path.exists()
        assert stories_path.is_dir()
        assert qa_path.exists()
        assert qa_path.is_dir()
        assert qa_gates_path.exists()
        assert qa_gates_path.is_dir()
        assert qa_assessments_path.exists()
        assert qa_assessments_path.is_dir()

    def test_validate_folder_structure_handles_errors(self):
        """Test that validate_folder_structure handles permission errors gracefully."""
        with patch("os.makedirs", side_effect=PermissionError("Permission denied")):
            result = self.writer.validate_folder_structure()
            assert result is False

    def test_write_artefact_prd(self):
        """Test writing PRD artefact."""
        content = "# Test PRD\n\nThis is a test PRD document."
        result = self.writer.write_artefact("prd", content)

        assert result is True

        prd_path = self.temp_dir / "docs" / "prd.md"
        assert prd_path.exists()
        assert prd_path.read_text() == content

    def test_write_artefact_story(self):
        """Test writing story artefact."""
        content = "# Test Story\n\n## Status: Draft\n\nTest story content."
        result = self.writer.write_artefact(
            "stories", content, epic_num=1, story_num=2, story_title="Test Story Title"
        )

        assert result is True

        story_path = (
            self.temp_dir / "docs" / "stories" / "1.2.test-story-title.story.md"
        )
        assert story_path.exists()
        assert story_path.read_text() == content

    def test_write_artefact_qa_gate(self):
        """Test writing QA gate artefact."""
        gate_data = {
            "schema": 1,
            "story": "1.2",
            "gate": "PASS",
            "status_reason": "Test gate",
            "reviewer": "Test",
            "top_issues": [],
        }
        result = self.writer.write_artefact(
            "qa_gates", gate_data, epic_num=1, story_num=2, story_slug="test-story"
        )

        assert result is True

        gate_path = self.temp_dir / "docs" / "qa" / "gates" / "1.2-test-story.yml"
        assert gate_path.exists()
        content = gate_path.read_text()
        assert "schema: 1" in content
        assert "gate: PASS" in content

    def test_write_artefact_qa_assessment(self):
        """Test writing QA assessment artefact."""
        content = "# Test Assessment\n\nThis is a test assessment."
        result = self.writer.write_artefact(
            "qa_assessments", content, epic_num=1, story_num=2, assessment_type="risk"
        )

        assert result is True

        assessment_path = self.temp_dir / "docs" / "qa" / "assessments"
        # Find the file with the correct pattern
        files = list(assessment_path.glob("1.2-risk-*.md"))
        assert len(files) == 1
        assert files[0].read_text() == content

    def test_write_artefact_unknown_type(self):
        """Test writing artefact with unknown type."""
        content = "Test content"
        result = self.writer.write_artefact("unknown_type", content)

        assert result is False

    def test_write_artefact_empty_content(self):
        """Test writing artefact with empty content."""
        result = self.writer.write_artefact("prd", "")

        assert result is False

    def test_write_artefact_validation_warnings(self):
        """Test that artefact validation provides appropriate warnings."""
        # Test PRD without expected structure
        content = "This is not a proper PRD"
        with patch("src.bmad_crewai.artefact_writer.logger") as mock_logger:
            result = self.writer.write_artefact("prd", content)
            assert result is True  # Should succeed but warn
            mock_logger.warning.assert_called()

    def test_write_file_with_backup(self):
        """Test _write_file creates backup when file exists."""
        file_path = self.temp_dir / "test.txt"
        file_path.write_text("original content")

        new_content = "new content"
        result = self.writer._write_file(file_path, new_content)

        assert result is True
        assert file_path.read_text() == new_content

        # Backup should be cleaned up after successful write
        backup_path = file_path.with_suffix(".bak")
        assert not backup_path.exists()

    def test_write_file_rollback_on_failure(self):
        """Test _write_file rolls back on failure."""
        file_path = self.temp_dir / "test.txt"
        original_content = "original content"
        file_path.write_text(original_content)

        with patch("builtins.open", side_effect=OSError("Write failed")):
            result = self.writer._write_file(file_path, "new content")

            assert result is False
            # Original content should be restored
            assert file_path.read_text() == original_content

    def test_check_disk_space(self):
        """Test disk space checking."""
        # Test with sufficient space
        result = self.writer._check_disk_space(self.temp_dir, 1024)
        assert result is True

        # Test with insufficient space
        with patch("os.statvfs") as mock_statvfs:
            mock_stat = mock_statvfs.return_value
            mock_stat.f_bavail = 0
            mock_stat.f_frsize = 1024
            result = self.writer._check_disk_space(self.temp_dir, 2048)
            assert result is False

    def test_create_filename_slug(self):
        """Test filename slug creation."""
        # Test basic slug creation
        slug = self.writer._create_filename_slug("Test Story Title!")
        assert slug == "test-story-title"

        # Test special characters removal
        slug = self.writer._create_filename_slug("Hello@World#Test")
        assert slug == "helloworldtest"

        # Test length limiting
        long_title = "A" * 60
        slug = self.writer._create_filename_slug(long_title)
        assert len(slug) <= 50

    def test_ensure_directory_structure_legacy(self):
        """Test legacy ensure_directory_structure method."""
        result = self.writer.ensure_directory_structure()
        assert result is True

        # Verify directories were created
        assert (self.temp_dir / "docs").exists()
        assert (self.temp_dir / "docs" / "stories").exists()
        assert (self.temp_dir / "docs" / "qa" / "gates").exists()
        assert (self.temp_dir / "docs" / "qa" / "assessments").exists()

    def test_write_prd_method(self):
        """Test write_prd method directly."""
        content = "# Test PRD\n\nContent"
        result = self.writer.write_prd(content)

        assert result is True
        prd_path = self.temp_dir / "docs" / "prd.md"
        assert prd_path.exists()
        assert prd_path.read_text() == content

    def test_write_story_method(self):
        """Test write_story method directly."""
        content = "# Test Story\n\nContent"
        result = self.writer.write_story(content, 1, 3, "Test Story")

        assert result is True
        story_path = self.temp_dir / "docs" / "stories" / "1.3.test-story.story.md"
        assert story_path.exists()
        assert story_path.read_text() == content

    def test_write_quality_gate_method(self):
        """Test write_quality_gate method directly."""
        gate_data = {"test": "data"}
        result = self.writer.write_quality_gate(gate_data, 2, 1, "test-gate")

        assert result is True
        gate_path = self.temp_dir / "docs" / "qa" / "gates" / "2.1-test-gate.yml"
        assert gate_path.exists()
        content = gate_path.read_text()
        assert "test: data" in content
        assert "updated:" in content  # Should have timestamp added

    def test_write_assessment_method(self):
        """Test write_assessment method directly."""
        content = "# Test Assessment\n\nContent"
        result = self.writer.write_assessment(content, 1, 5, "nfr")

        assert result is True
        assessment_path = self.temp_dir / "docs" / "qa" / "assessments"
        files = list(assessment_path.glob("1.5-nfr-*.md"))
        assert len(files) == 1
        assert files[0].read_text() == content

    def test_write_epic_method(self):
        """Test write_epic method directly."""
        content = "# Test Epic\n\nContent"
        result = self.writer.write_epic(content, 3, "Test Epic Title")

        assert result is True
        epic_path = self.temp_dir / "docs" / "epics" / "epic-3-test-epic-title.md"
        assert epic_path.exists()
        assert epic_path.read_text() == content
