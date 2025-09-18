"""Test template loading functionality."""

from pathlib import Path
from unittest.mock import patch

import pytest

from bmad_crewai.core import BmadCrewAI
from bmad_crewai.exceptions import TemplateError


class TestTemplateLoading:
    """Test cases for BMAD template loading functionality."""

    def test_template_directory_exists(self):
        """Test that template directory exists."""
        template_dir = Path(".bmad-core/templates")
        assert template_dir.exists(), "Template directory should exist"
        assert template_dir.is_dir(), "Template directory should be a directory"

    def test_template_files_exist(self):
        """Test that template files exist."""
        template_dir = Path(".bmad-core/templates")
        template_files = list(template_dir.glob("*.yaml"))

        assert len(template_files) > 0, "Should have at least one template file"

        # Check for story template specifically
        story_template = template_dir / "story-tmpl.yaml"
        assert story_template.exists(), "Story template should exist"

    def test_bmad_crewai_initialization(self):
        """Test BmadCrewAI can be initialized."""
        bmad = BmadCrewAI()
        assert bmad is not None, "BmadCrewAI should initialize successfully"

    @pytest.mark.asyncio
    async def test_template_loading_workflow(self):
        """Test the complete template loading workflow."""
        bmad = BmadCrewAI()

        async with bmad.session():
            # Load templates
            loaded_templates = bmad.load_bmad_templates()

            # Check that templates were loaded
            templates = bmad.list_templates()
            assert isinstance(templates, dict), "Should return template dictionary"

            # Check for story template
            assert len(templates) > 0, "Should have loaded at least one template"

    @pytest.mark.asyncio
    async def test_template_validation(self):
        """Test template validation functionality."""
        bmad = BmadCrewAI()

        async with bmad.session():
            loaded_templates = bmad.load_bmad_templates()

            # Test validation for a known template
            templates = bmad.list_templates()
            if templates:
                template_id = list(templates.keys())[0]
                is_valid = bmad.validate_template_dependencies(template_id)
                assert is_valid is True, f"Template {template_id} should be valid"

    def test_template_info_structure(self):
        """Test TemplateInfo dataclass structure."""
        from bmad_crewai.template_manager import TemplateInfo

        template_info = TemplateInfo(
            id="test-template",
            name="Test Template",
            version="1.0",
            template_path=Path(".bmad-core/templates/story-tmpl.yaml"),
            workflow_mode="interactive",
            sections={},
            agent_config={},
        )

        assert template_info.id == "test-template"
        assert template_info.name == "Test Template"
        assert template_info.workflow_mode == "interactive"
        assert isinstance(template_info.template_path, Path)
