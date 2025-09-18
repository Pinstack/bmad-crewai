"""Tests for ArtefactManager functionality."""

from unittest.mock import MagicMock, patch

import pytest

from src.bmad_crewai.artefact_manager import (
    ArtefactManager,
    ArtefactType,
    BmadArtefactGenerator,
)


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


class TestBmadArtefactGenerator:
    """Test suite for BmadArtefactGenerator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_writer = MagicMock()
        self.generator = BmadArtefactGenerator(self.mock_writer)

    def test_init_with_writer(self):
        """Test BmadArtefactGenerator initialization with custom writer."""
        generator = BmadArtefactGenerator(self.mock_writer)
        assert generator.artefact_writer == self.mock_writer
        assert hasattr(generator, "logger")

    def test_detect_artefact_type_prd(self):
        """Test artefact type detection for PRD."""
        content = "# Product Requirements Document\n\nThis is a PRD."
        result = self.generator.detect_artefact_type(content)
        assert result == ArtefactType.PRD

    def test_detect_artefact_type_story(self):
        """Test artefact type detection for story."""
        content = "# Story\n\n**As a** user,\n**I want** feature,\n**so that** value."
        result = self.generator.detect_artefact_type(content)
        assert result == ArtefactType.STORIES

    def test_detect_artefact_type_gate(self):
        """Test artefact type detection for quality gate."""
        content = "schema: 1\ngate: PASS\nstatus_reason: Test gate"
        result = self.generator.detect_artefact_type(content)
        assert result == ArtefactType.QA_GATES

    def test_detect_artefact_type_assessment(self):
        """Test artefact type detection for assessment."""
        content = "# Risk Assessment\n\nThis is an assessment document."
        result = self.generator.detect_artefact_type(content)
        assert result == ArtefactType.QA_ASSESSMENTS

    def test_detect_artefact_type_epic(self):
        """Test artefact type detection for epic."""
        content = "# Epic\n\n## Epic Goal\n\nEpic description."
        result = self.generator.detect_artefact_type(content)
        assert result == ArtefactType.EPICS

    def test_detect_artefact_type_template(self):
        """Test artefact type detection for template."""
        content = "template: {{placeholder}}\n{{variable}}"
        result = self.generator.detect_artefact_type(content)
        assert result == ArtefactType.TEMPLATES

    def test_detect_artefact_type_default(self):
        """Test default artefact type detection."""
        content = "Some random content without markers"
        result = self.generator.detect_artefact_type(content)
        assert result == ArtefactType.STORIES  # Default fallback

    def test_detect_artefact_type_with_context(self):
        """Test artefact type detection with context override."""
        content = "Random content"
        context = {"type": "qa_gates"}
        result = self.generator.detect_artefact_type(content, context)
        assert result == ArtefactType.QA_GATES

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_generate_artefact_success(self, mock_writer_class):
        """Test successful artefact generation."""
        mock_writer = MagicMock()
        mock_writer.write_artefact.return_value = True
        mock_writer_class.return_value = mock_writer

        generator = BmadArtefactGenerator(mock_writer)
        result = generator.generate_artefact(
            ArtefactType.STORIES, "# Test Story", story_title="Test"
        )

        assert result is True
        mock_writer.write_artefact.assert_called_once()

    def test_generate_artefact_validation_failure(self):
        """Test artefact generation with validation failure."""
        # Empty content should fail validation
        result = self.generator.generate_artefact(ArtefactType.STORIES, "")
        assert result is False

    def test_generate_artefact_processing(self):
        """Test artefact content processing."""
        content = "Test content"
        processed = self.generator._process_content(ArtefactType.STORIES, content)
        assert processed == content  # Basic processing

    def test_generate_artefact_status_processing(self):
        """Test story status processing."""
        content = "Test story without status"
        processed = self.generator._process_content(ArtefactType.STORIES, content)
        assert "## Status: Draft" in processed

    def test_generate_artefact_gate_processing(self):
        """Test quality gate schema processing."""
        content = "gate: PASS"
        processed = self.generator._process_content(ArtefactType.QA_GATES, content)
        assert "schema: 1" in processed

    def test_add_cross_references(self):
        """Test cross-reference addition."""
        content = "Test content"
        result = self.generator._add_cross_references(ArtefactType.STORIES, content)
        assert result == content  # Currently returns content as-is

    def test_write_artefact_success(self):
        """Test successful artefact writing."""
        self.mock_writer.write_artefact.return_value = True
        result = self.generator._write_artefact(ArtefactType.STORIES, "content")
        assert result is True

    def test_write_artefact_failure(self):
        """Test failed artefact writing."""
        self.mock_writer.write_artefact.return_value = False
        result = self.generator._write_artefact(ArtefactType.STORIES, "content")
        assert result is False


class TestArtefactManagerComprehensive:
    """Test suite for enhanced ArtefactManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ArtefactManager()

    @patch("src.bmad_crewai.artefact_manager.BMADArtefactWriter")
    def test_init_with_generator(self, mock_writer_class):
        """Test that ArtefactManager initializes with artefact generator."""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        manager = ArtefactManager()
        assert hasattr(manager, "artefact_generator")
        assert isinstance(manager.artefact_generator, BmadArtefactGenerator)

    @patch("src.bmad_crewai.artefact_manager.BmadArtefactGenerator")
    def test_generate_comprehensive_artefact_success(self, mock_generator_class):
        """Test comprehensive artefact generation."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_artefact.return_value = True

        manager = ArtefactManager()
        manager.artefact_generator = mock_generator

        result = manager.generate_comprehensive_artefact(
            "content", artefact_type="stories"
        )

        assert result is True
        mock_generator.generate_artefact.assert_called_once()

    @patch("src.bmad_crewai.artefact_manager.BmadArtefactGenerator")
    def test_generate_comprehensive_artefact_auto_detect(self, mock_generator_class):
        """Test comprehensive artefact generation with auto-detection."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.detect_artefact_type.return_value = ArtefactType.STORIES
        mock_generator.generate_artefact.return_value = True

        manager = ArtefactManager()
        manager.artefact_generator = mock_generator

        result = manager.generate_comprehensive_artefact("# Story content")

        assert result is True
        mock_generator.detect_artefact_type.assert_called_once_with(
            "# Story content", None
        )
        mock_generator.generate_artefact.assert_called_once()

    def test_validate_artefact_consistency_valid_story(self):
        """Test artefact consistency validation for valid story."""
        content = """# Story Test

## Status: Draft

## Story

**As a** user,
**I want** feature,
**so that** value.

## Acceptance Criteria

1. Test criterion
"""
        result = self.manager.validate_artefact_consistency("stories", content)

        assert result["consistent"] is True
        assert len(result["cross_references"]) >= 0

    def test_validate_artefact_consistency_invalid_story(self):
        """Test artefact consistency validation for invalid story."""
        content = "Invalid story content without proper structure"
        result = self.manager.validate_artefact_consistency("stories", content)

        assert result["consistent"] is False
        assert len(result["issues"]) > 0

    def test_validate_artefact_consistency_valid_gate(self):
        """Test artefact consistency validation for valid gate."""
        content = """schema: 1
story: "1.1"
gate: PASS
reviewer: "Test"
updated: "2024-01-01T00:00:00Z"
"""
        result = self.manager.validate_artefact_consistency("qa_gates", content)

        assert result["consistent"] is True

    def test_validate_artefact_consistency_invalid_gate(self):
        """Test artefact consistency validation for invalid gate."""
        content = "Invalid gate content without schema"
        result = self.manager.validate_artefact_consistency("qa_gates", content)

        assert result["consistent"] is False
        assert len(result["issues"]) > 0
