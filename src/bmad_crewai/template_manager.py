"""Template loading and validation functionality."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .exceptions import TemplateError

logger = logging.getLogger(__name__)


class TemplateInfo:
    """Information about a loaded BMAD template."""

    def __init__(
        self,
        id: str,
        name: str,
        version: str,
        template_path: Path,
        workflow_mode: str,
        sections: Dict[str, Any],
        agent_config: Dict[str, Any],
    ):
        self.id = id
        self.name = name
        self.version = version
        self.template_path = template_path
        self.workflow_mode = workflow_mode
        self.sections = sections
        self.agent_config = agent_config


class TemplateManager:
    """Manager for loading and validating BMAD templates."""

    def __init__(self, templates_path: Optional[Path] = None):
        self.templates_path = templates_path or Path(".bmad-core/templates")
        self.templates: Dict[str, TemplateInfo] = {}

    def load_templates(self) -> Dict[str, TemplateInfo]:
        """Load all BMAD templates from the templates directory.

        Returns:
            Dict[str, TemplateInfo]: Dictionary mapping template IDs to template info

        Raises:
            TemplateError: If template loading or validation fails
        """
        templates_dir = self.templates_path
        if not templates_dir.exists():
            logger.warning(f"Templates directory not found: {templates_dir}")
            return {}

        for template_file in templates_dir.glob("*.yaml"):
            try:
                template_id = template_file.stem
                template_info = self._load_single_template(template_file)
                self.templates[template_id] = template_info
                logger.debug(f"Loaded template: {template_id}")
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
                raise TemplateError(f"Failed to load template {template_file}: {e}")

        logger.info(f"Loaded {len(self.templates)} templates")
        return self.templates

    def _load_single_template(self, template_path: Path) -> TemplateInfo:
        """Load a single template from file.

        Args:
            template_path: Path to the template YAML file

        Returns:
            TemplateInfo: Parsed template information

        Raises:
            TemplateError: If template parsing or validation fails
        """
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_data = yaml.safe_load(f)
        except Exception as e:
            raise TemplateError(f"Failed to parse template {template_path}: {e}")

        if not template_data:
            raise TemplateError(f"Empty template file: {template_path}")

        # Extract template metadata
        template_meta = template_data.get("template", {})
        workflow = template_data.get("workflow", {})
        agent_config = template_data.get("agent_config", {})
        sections_data = template_data.get("sections", [])

        # Validate required template metadata
        required_fields = ["id", "name", "version"]
        for required_field in required_fields:
            if required_field not in template_meta:
                raise TemplateError(
                    f"Missing required field '{required_field}' "
                    f"in template {template_path}"
                )

        # Validate template ID format
        template_id = template_meta["id"]
        if not isinstance(template_id, str) or not template_id.strip():
            raise TemplateError(f"Invalid template ID: {template_id}")

        # Extract workflow mode
        workflow_mode = workflow.get("mode", "interactive")
        if workflow_mode not in ["interactive", "batch", "automated"]:
            logger.warning(
                f"Unknown workflow mode '{workflow_mode}' in "
                f"{template_path}, defaulting to 'interactive'"
            )
            workflow_mode = "interactive"

        # Validate sections structure
        if not isinstance(sections_data, list):
            raise TemplateError(f"Sections must be a list in template {template_path}")

        # Convert sections list to dictionary by ID for easier access
        sections_dict = {}
        for section in sections_data:
            if not isinstance(section, dict) or "id" not in section:
                raise TemplateError(
                    f"Invalid section format in template {template_path}"
                )
            sections_dict[section["id"]] = section

        # Extract agent assignments and validate
        editable_sections = agent_config.get("editable_sections", [])
        if not isinstance(editable_sections, list):
            raise TemplateError(
                f"editable_sections must be a list in template {template_path}"
            )

        # Validate agent ownership in sections
        for section_id, section in sections_dict.items():
            if "owner" not in section:
                logger.warning(
                    f"Section '{section_id}' missing owner in {template_path}"
                )
            if "editors" in section and not isinstance(section["editors"], list):
                raise TemplateError(
                    f"editors must be a list for section '{section_id}' "
                    f"in {template_path}"
                )

        return TemplateInfo(
            id=template_meta["id"],
            name=template_meta["name"],
            version=template_meta["version"],
            template_path=template_path,
            workflow_mode=workflow_mode,
            sections=sections_dict,
            agent_config=agent_config,
        )

    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        """Get a loaded template by ID.

        Args:
            template_id: Template identifier

        Returns:
            TemplateInfo or None: Template information if found
        """
        return self.templates.get(template_id)

    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all loaded templates with basic information.

        Returns:
            Dict[str, Dict[str, Any]]: Template summaries by ID
        """
        return {
            template_id: {
                "name": info.name,
                "version": info.version,
                "workflow_mode": info.workflow_mode,
                "sections_count": len(info.sections),
            }
            for template_id, info in self.templates.items()
        }

    def validate_template_dependencies(self, template_id: str) -> bool:
        """Validate that a template's dependencies are satisfied.

        Args:
            template_id: Template identifier to validate

        Returns:
            bool: True if dependencies are satisfied

        Raises:
            TemplateError: If dependencies are not satisfied
        """
        template = self.get_template(template_id)
        if not template:
            raise TemplateError(f"Template not found: {template_id}")

        # Check for required agent configurations
        required_agents = [
            "scrum-master",
            "product-owner",
            "dev-agent",
            "qa-agent",
            "product-manager",
            "architect",
        ]
        # In future, this could check actual agent availability

        # For now, just log warnings about agent dependencies
        for section_id, section in template.sections.items():
            owner = section.get("owner")
            if owner and owner not in required_agents:
                logger.warning(
                    f"Unknown agent '{owner}' required for section "
                    f"'{section_id}' in template {template_id}"
                )

        # Check for template-specific dependencies
        workflow = template.workflow_mode
        if workflow == "automated" and not template.agent_config.get(
            "allow_automated", False
        ):
            raise TemplateError(
                f"Template {template_id} has automated workflow but "
                f"doesn't allow automated execution"
            )

        return True
