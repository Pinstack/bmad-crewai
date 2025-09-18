"""Tests for ArtefactManager functionality."""

from unittest.mock import MagicMock, patch

import pytest

from src.bmad_crewai.artefact_manager import ArtefactManager


class TestArtefactManager:
    """Test suite for ArtefactManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ArtefactManager()

    def test_init_creates_writer(self):
        """Test that ArtefactManager initializes with BMADArtefactWriter."""
        assert hasattr(self.manager, "artefact_writer")
        assert hasattr(self.manager, "logger")

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_write_artefact_prd(self, mock_writer_class):
        """Test writing PRD artefact."""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        mock_writer.write_artefact.return_value = True

        manager = ArtefactManager()
        result = manager.write_artefact("prd", "test content", filename="test.md")

        assert result is True
        mock_writer.write_artefact.assert_called_once_with(
            "prd", "test content", filename="test.md"
        )

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_write_artefact_story(self, mock_writer_class):
        """Test writing story artefact."""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        mock_writer.write_artefact.return_value = True

        manager = ArtefactManager()
        result = manager.write_artefact(
            "story", "story content", epic_num=1, story_num=2, story_title="Test"
        )

        assert result is True
        mock_writer.write_artefact.assert_called_once_with(
            "stories", "story content", epic_num=1, story_num=2, story_title="Test"
        )

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_write_artefact_gate(self, mock_writer_class):
        """Test writing gate artefact."""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        mock_writer.write_artefact.return_value = True

        manager = ArtefactManager()
        result = manager.write_artefact(
            "gate", {"test": "data"}, epic_num=1, story_num=2, story_slug="test"
        )

        assert result is True
        mock_writer.write_artefact.assert_called_once_with(
            "qa_gates", {"test": "data"}, epic_num=1, story_num=2, story_slug="test"
        )

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_write_artefact_assessment(self, mock_writer_class):
        """Test writing assessment artefact."""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        mock_writer.write_artefact.return_value = True

        manager = ArtefactManager()
        result = manager.write_artefact(
            "assessment",
            "assessment content",
            epic_num=1,
            story_num=2,
            assessment_type="risk",
        )

        assert result is True
        mock_writer.write_artefact.assert_called_once_with(
            "qa_assessments",
            "assessment content",
            epic_num=1,
            story_num=2,
            assessment_type="risk",
        )

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_write_artefact_epic(self, mock_writer_class):
        """Test writing epic artefact."""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        mock_writer.write_artefact.return_value = True

        manager = ArtefactManager()
        result = manager.write_artefact(
            "epic", "epic content", epic_num=3, epic_title="Test Epic"
        )

        assert result is True
        mock_writer.write_artefact.assert_called_once_with(
            "epics", "epic content", epic_num=3, epic_title="Test Epic"
        )

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_write_artefact_unknown_type(self, mock_writer_class):
        """Test writing artefact with unknown type."""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        mock_writer.write_artefact.return_value = False

        manager = ArtefactManager()
        result = manager.write_artefact("unknown", "content")

        assert result is False
        mock_writer.write_artefact.assert_called_once_with("unknown", "content")

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_write_artefact_exception_handling(self, mock_writer_class):
        """Test exception handling in write_artefact."""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        mock_writer.write_artefact.side_effect = Exception("Test error")

        manager = ArtefactManager()
        result = manager.write_artefact("prd", "content")

        assert result is False

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_test_artefact_generation(self, mock_writer_class):
        """Test test_artefact_generation method."""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        mock_writer.test_artefact_writing.return_value = {"test": "result"}

        manager = ArtefactManager()
        result = manager.test_artefact_generation()

        assert result == {"test": "result"}
        mock_writer.test_artefact_writing.assert_called_once()

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_test_artefact_generation_exception(self, mock_writer_class):
        """Test exception handling in test_artefact_generation."""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        mock_writer.test_artefact_writing.side_effect = Exception("Test error")

        manager = ArtefactManager()
        result = manager.test_artefact_generation()

        assert result == {"error": "Test error"}
