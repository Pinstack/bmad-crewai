"""Artefact writer for BMAD folder structure generation."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BMADArtefactWriter:
    """Handles writing artefacts to BMAD folder structure.

    This component manages the creation and writing of artefacts to the
    standardized BMAD folder structure (docs/, stories/, qa/, etc.).
    """

    # FOLDER_MAPPING dictionary mapping artefact types to output paths
    FOLDER_MAPPING = {
        "prd": "docs/prd.md",  # Single file artefact
        "architecture": "docs/architecture/",  # Directory for sharded docs
        "stories": "docs/stories/",  # Directory for story files
        "qa_assessments": "docs/qa/assessments/",  # QA assessment files
        "qa_gates": "docs/qa/gates/",  # Quality gate files
        "epics": "docs/epics/",  # Epic documentation
        "templates": "docs/templates/",  # Template storage
        # Additional comprehensive document types
        "brief": "docs/brief.md",  # Project brief document
        "research": "docs/research/",  # Research documentation
        "specifications": "docs/specifications/",  # Technical specifications
        "diagrams": "docs/diagrams/",  # Architecture diagrams
        "protocols": "docs/protocols/",  # Communication protocols
        "guides": "docs/guides/",  # User/developer guides
    }

    def __init__(self, base_path: Optional[str] = None):
        """Initialize the artefact writer.

        Args:
            base_path: Base path for artefact writing (defaults to current directory)
        """
        self.base_path = Path(base_path or ".")
        self.docs_path = self.base_path / "docs"
        self.stories_path = self.docs_path / "stories"
        self.qa_path = self.docs_path / "qa"
        self.qa_gates_path = self.qa_path / "gates"
        self.qa_assessments_path = self.qa_path / "assessments"

        logger.info(f"Artefact writer initialized with base path: {self.base_path}")

        # Initialize artefact metadata tracking
        self.artefact_metadata = {}

    def validate_artefact_naming_conventions(
        self, artefact_type: str, filename: str
    ) -> Dict[str, Any]:
        """Validate artefact naming conventions and provide suggestions.

        Args:
            artefact_type: Type of artefact
            filename: Proposed filename

        Returns:
            Dict with validation results and suggestions
        """
        results = {
            "valid": True,
            "issues": [],
            "suggestions": [],
            "conventions_applied": [],
        }

        try:
            # Apply type-specific naming conventions
            if artefact_type == "stories":
                # Stories should follow: {epic_num}.{story_num}.{story_title_short}.story.md
                if not filename.endswith(".story.md"):
                    results["issues"].append("Story files should end with '.story.md'")
                    results["suggestions"].append(
                        f"Rename to: {filename.replace('.md', '.story.md')}"
                    )
                    results["valid"] = False
                else:
                    results["conventions_applied"].append(
                        "Story naming convention applied"
                    )

            elif artefact_type == "qa_gates":
                # Gates should follow: {epic_num}.{story_num}-{story_slug}.yml
                if not filename.endswith(".yml"):
                    results["issues"].append("Gate files should end with '.yml'")
                    results["suggestions"].append(
                        f"Convert to YAML: {filename.replace('.md', '.yml')}"
                    )
                    results["valid"] = False
                else:
                    results["conventions_applied"].append(
                        "Gate naming convention applied"
                    )

            elif artefact_type == "qa_assessments":
                # Assessments should follow: {epic_num}.{story_num}-{assessment_type}-{YYYYMMDD}.md
                import re

                if not re.search(r"\d{8}\.md$", filename):
                    results["issues"].append(
                        "Assessment files should include date in YYYYMMDD format"
                    )
                    from datetime import datetime

                    date_str = datetime.now().strftime("%Y%m%d")
                    base_name = filename.replace(".md", "")
                    results["suggestions"].append(
                        f"Add date: {base_name}-{date_str}.md"
                    )
                    results["valid"] = False
                else:
                    results["conventions_applied"].append(
                        "Assessment naming convention applied"
                    )

            elif artefact_type == "epics":
                # Epics should follow: epic-{epic_num}-{epic_title_short}.md
                if not filename.startswith("epic-"):
                    results["issues"].append("Epic files should start with 'epic-'")
                    results["suggestions"].append(f"Rename to: epic-{filename}")
                    results["valid"] = False
                else:
                    results["conventions_applied"].append(
                        "Epic naming convention applied"
                    )

            # General conventions
            if len(filename) > 100:
                results["issues"].append("Filename too long (>100 characters)")
                results["suggestions"].append(
                    "Shorten filename to under 100 characters"
                )

            # Check for invalid characters
            invalid_chars = ["<", ">", ":", '"', "|", "?", "*"]
            if any(char in filename for char in invalid_chars):
                results["issues"].append("Filename contains invalid characters")
                results["suggestions"].append(
                    'Remove special characters: < > : " | ? *'
                )

        except Exception as e:
            results["valid"] = False
            results["issues"].append(f"Naming validation error: {e}")

        return results

    def track_artefact_metadata(
        self, artefact_type: str, filename: str, metadata: Dict[str, Any]
    ):
        """Track artefact metadata for version management and dependencies.

        Args:
            artefact_type: Type of artefact
            filename: Artefact filename
            metadata: Metadata to track
        """
        if artefact_type not in self.artefact_metadata:
            self.artefact_metadata[artefact_type] = {}

        self.artefact_metadata[artefact_type][filename] = {
            "created": metadata.get("created", datetime.now().isoformat()),
            "version": metadata.get("version", "1.0"),
            "dependencies": metadata.get("dependencies", []),
            "last_modified": datetime.now().isoformat(),
            **metadata,
        }

        logger.debug(f"Tracked metadata for {artefact_type}/{filename}")

    def get_artefact_dependencies(self, artefact_type: str, filename: str) -> list:
        """Get dependencies for an artefact.

        Args:
            artefact_type: Type of artefact
            filename: Artefact filename

        Returns:
            List of dependencies
        """
        try:
            return (
                self.artefact_metadata.get(artefact_type, {})
                .get(filename, {})
                .get("dependencies", [])
            )
        except Exception:
            return []

    def validate_artefact_consistency(
        self, artefact_type: str, content: str, filename: str
    ) -> Dict[str, Any]:
        """Validate artefact consistency across the document set.

        Args:
            artefact_type: Type of artefact
            content: Artefact content
            filename: Artefact filename

        Returns:
            Dict with consistency validation results
        """
        results = {
            "consistent": True,
            "issues": [],
            "cross_references": [],
            "missing_references": [],
        }

        try:
            # Type-specific consistency checks
            if artefact_type == "stories":
                # Check for required sections
                required_sections = ["## Status:", "## Story", "## Acceptance Criteria"]
                for section in required_sections:
                    if section not in content:
                        results["issues"].append(f"Missing required section: {section}")
                        results["consistent"] = False

                # Check cross-references to architecture
                if "docs/architecture/" in content:
                    results["cross_references"].append(
                        "References architecture documents"
                    )

                # Check for referenced but potentially missing files
                import re

                refs = re.findall(r"docs/[^)]+", content)
                for ref in refs:
                    # This is a basic check - could be enhanced with actual file existence validation
                    results["cross_references"].append(f"References: {ref}")

            elif artefact_type == "qa_gates":
                # Check for required gate fields
                required_fields = ["schema:", "story:", "gate:"]
                content_lower = content.lower()
                for field in required_fields:
                    if field not in content_lower:
                        results["issues"].append(
                            f"Missing required gate field: {field}"
                        )
                        results["consistent"] = False

            # Track this artefact's metadata
            self.track_artefact_metadata(
                artefact_type,
                filename,
                {
                    "content_length": len(content),
                    "sections_count": content.count("##"),
                    "references_count": len(results["cross_references"]),
                },
            )

        except Exception as e:
            results["consistent"] = False
            results["issues"].append(f"Consistency validation error: {e}")

        return results

    def validate_folder_structure(self) -> bool:
        """Ensure all required directories exist before writing artefacts.

        Returns:
            bool: True if all directories created successfully
        """
        success = True

        for artefact_type, path in self.FOLDER_MAPPING.items():
            full_path = self.base_path / path

            if path.endswith("/"):  # Directory path
                try:
                    os.makedirs(full_path, exist_ok=True)
                    logger.info(f"Ensured directory exists: {full_path}")
                except (OSError, PermissionError) as e:
                    logger.error(f"Failed to create directory {full_path}: {e}")
                    success = False
            else:  # File path - ensure parent directory exists
                try:
                    parent_dir = full_path.parent
                    os.makedirs(parent_dir, exist_ok=True)
                    logger.info(f"Ensured parent directory exists for: {full_path}")
                except (OSError, PermissionError) as e:
                    logger.error(
                        f"Failed to create parent directory for {full_path}: {e}"
                    )
                    success = False

        return success

    def ensure_directory_structure(self):
        """Legacy method for backward compatibility."""
        return self.validate_folder_structure()

    def write_prd(self, content: str, filename: str = "prd.md") -> bool:
        """Write PRD content to docs/prd.md.

        Args:
            content: PRD markdown content
            filename: Target filename (default: prd.md)

        Returns:
            bool: True if successful
        """
        try:
            prd_path = self.docs_path / filename
            success = self._write_file(prd_path, content)
            if success:
                logger.info(f"PRD written to: {prd_path}")
            return success
        except Exception as e:
            logger.error(f"Failed to write PRD: {e}")
            return False

    def write_story(
        self, story_content: str, epic_num: int, story_num: int, story_title: str
    ) -> bool:
        """Write user story to docs/stories/ directory.

        Args:
            story_content: Complete story markdown content
            epic_num: Epic number
            story_num: Story number
            story_title: Story title for filename

        Returns:
            bool: True if successful
        """
        try:
            # Create filename: {epic_num}.{story_num}.{story_title_short}.story.md
            title_short = self._create_filename_slug(story_title)
            filename = f"{epic_num}.{story_num}.{title_short}.story.md"
            story_path = self.stories_path / filename

            success = self._write_file(story_path, story_content)
            if success:
                logger.info(f"Story written to: {story_path}")
            return success
        except Exception as e:
            logger.error(f"Failed to write story: {e}")
            return False

    def write_quality_gate(
        self, gate_data: Dict[str, Any], epic_num: int, story_num: int, story_slug: str
    ) -> bool:
        """Write quality gate decision to qa/gates/ directory.

        Args:
            gate_data: Gate data dictionary
            epic_num: Epic number
            story_num: Story number
            story_slug: Story slug for filename

        Returns:
            bool: True if successful
        """
        try:
            import yaml

            filename = f"{epic_num}.{story_num}-{story_slug}.yml"
            gate_path = self.qa_gates_path / filename

            # Add timestamp if not present
            if "updated" not in gate_data:
                gate_data["updated"] = datetime.now().isoformat()

            yaml_content = yaml.dump(
                gate_data, default_flow_style=False, sort_keys=False
            )
            success = self._write_file(gate_path, yaml_content)
            if success:
                logger.info(f"Quality gate written to: {gate_path}")
            return success
        except Exception as e:
            logger.error(f"Failed to write quality gate: {e}")
            return False

    def write_assessment(
        self,
        assessment_content: str,
        epic_num: int,
        story_num: int,
        assessment_type: str,
    ) -> bool:
        """Write assessment document to qa/assessments/ directory.

        Args:
            assessment_content: Assessment markdown content
            epic_num: Epic number
            story_num: Story number
            assessment_type: Type of assessment (e.g., 'risk', 'nfr', 'trace')

        Returns:
            bool: True if successful
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{epic_num}.{story_num}-{assessment_type}-{timestamp}.md"
            assessment_path = self.qa_assessments_path / filename

            success = self._write_file(assessment_path, assessment_content)
            if success:
                logger.info(f"Assessment written to: {assessment_path}")
            return success
        except Exception as e:
            logger.error(f"Failed to write assessment: {e}")
            return False

    def write_epic(self, epic_content: str, epic_num: int, epic_title: str) -> bool:
        """Write epic document to docs/epics/ directory.

        Args:
            epic_content: Epic markdown content
            epic_num: Epic number
            epic_title: Epic title for filename

        Returns:
            bool: True if successful
        """
        try:
            # Ensure directory structure exists
            if not self.validate_folder_structure():
                logger.error("Failed to ensure directory structure for epic writing")
                return False

            epics_path = self.docs_path / "epics"
            title_short = self._create_filename_slug(epic_title)
            filename = f"epic-{epic_num}-{title_short}.md"
            epic_path = epics_path / filename

            success = self._write_file(epic_path, epic_content)
            if success:
                logger.info(f"Epic written to: {epic_path}")
            return success
        except Exception as e:
            logger.error(f"Failed to write epic: {e}")
            return False

    def test_artefact_writing(self) -> Dict[str, bool]:
        """Test artefact writing functionality.

        Returns:
            Dict with test results for each artefact type
        """
        results = {
            "directory_structure": False,
            "prd_writing": False,
            "story_writing": False,
            "gate_writing": False,
            "assessment_writing": False,
            "epic_writing": False,
        }

        try:
            # Test directory structure creation
            results["directory_structure"] = self.ensure_directory_structure()

            # Test PRD writing
            test_prd = "# Test PRD\n\nThis is a test PRD document."
            results["prd_writing"] = self.write_prd(test_prd, "test-prd.md")

            # Test story writing
            test_story = "# Test Story\n\n## Status: Draft\n\nTest story content."
            results["story_writing"] = self.write_story(test_story, 1, 1, "test-story")

            # Test quality gate writing
            test_gate = {
                "schema": 1,
                "story": "1.1",
                "gate": "PASS",
                "status_reason": "Test gate for artefact writing validation",
                "reviewer": "Artefact Writer",
                "top_issues": [],
            }
            results["gate_writing"] = self.write_quality_gate(
                test_gate, 1, 1, "test-story"
            )

            # Test assessment writing
            test_assessment = "# Test Assessment\n\nThis is a test assessment."
            results["assessment_writing"] = self.write_assessment(
                test_assessment, 1, 1, "test"
            )

            # Test epic writing
            test_epic = "# Test Epic\n\n## Epic Goal\n\nTest epic content."
            results["epic_writing"] = self.write_epic(test_epic, 1, "test-epic")

            logger.info("Artefact writing tests completed")

        except Exception as e:
            logger.error(f"Artefact writing test failed: {e}")

        return results

    def _write_file(self, file_path: Path, content: str) -> bool:
        """Write content to file with comprehensive error handling and rollback.

        Args:
            file_path: Path to write to
            content: Content to write

        Returns:
            bool: True if successful
        """
        backup_path = None

        try:
            # Check disk space before writing
            if not self._check_disk_space(file_path.parent):
                logger.error(f"Insufficient disk space for writing to {file_path}")
                return False

            # Create backup if file exists
            if file_path.exists():
                backup_path = file_path.with_suffix(".bak")
                try:
                    file_path.rename(backup_path)
                    logger.debug(f"Created backup: {backup_path}")
                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not create backup for {file_path}: {e}")
                    backup_path = None

            # Ensure parent directory exists
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                logger.error(
                    f"Failed to create parent directory {file_path.parent}: {e}"
                )
                return False

            # Write content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Verify write was successful
            if not file_path.exists():
                logger.error(f"File write verification failed for {file_path}")
                return False

            # Clean up backup on success
            if backup_path and backup_path.exists():
                try:
                    backup_path.unlink()
                    logger.debug(f"Removed backup: {backup_path}")
                except OSError as e:
                    logger.warning(f"Could not remove backup {backup_path}: {e}")

            logger.info(f"Successfully wrote artefact to: {file_path}")
            return True

        except (OSError, PermissionError) as e:
            logger.error(f"File system error writing to {file_path}: {e}")
            self._rollback_write(file_path, backup_path)
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing to {file_path}: {e}")
            self._rollback_write(file_path, backup_path)
            return False

    def _check_disk_space(self, path: Path, required_bytes: int = 1024) -> bool:
        """Check if there's sufficient disk space.

        Args:
            path: Path to check disk space for
            required_bytes: Minimum required bytes (default: 1KB)

        Returns:
            bool: True if sufficient space
        """
        try:
            stat = os.statvfs(path)
            available_bytes = stat.f_bavail * stat.f_frsize
            return available_bytes >= required_bytes
        except (OSError, AttributeError):
            # os.statvfs not available on Windows or other error
            logger.warning("Could not check disk space, proceeding anyway")
            return True

    def _rollback_write(self, file_path: Path, backup_path: Optional[Path]):
        """Rollback a failed write operation.

        Args:
            file_path: Original file path
            backup_path: Backup file path if it exists
        """
        try:
            # Remove partially written file if it exists
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Removed partially written file: {file_path}")

            # Restore from backup if available
            if backup_path and backup_path.exists():
                backup_path.rename(file_path)
                logger.info(f"Restored from backup: {backup_path} -> {file_path}")

        except OSError as e:
            logger.error(f"Rollback failed for {file_path}: {e}")

    def _create_filename_slug(self, title: str) -> str:
        """Create a filename-safe slug from a title.

        Args:
            title: Original title

        Returns:
            str: Slugified version
        """
        # Convert to lowercase, replace spaces and special chars with hyphens
        import re

        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)  # Remove special characters
        slug = re.sub(r"[\s_]+", "-", slug)  # Replace spaces/underscores with hyphens
        slug = re.sub(r"-+", "-", slug)  # Replace multiple hyphens with single
        slug = slug.strip("-")  # Remove leading/trailing hyphens

        # Limit length
        if len(slug) > 50:
            slug = slug[:50].rstrip("-")

        return slug or "untitled"

    def write_artefact(self, artefact_type: str, content: str, **kwargs) -> bool:
        """Write artefact to BMAD folder structure using comprehensive validation and naming conventions.

        Args:
            artefact_type: Type of artefact ('prd', 'stories', 'qa_assessments', etc.)
            content: Artefact content
            **kwargs: Additional parameters for specific artefact types

        Returns:
            bool: True if successful
        """
        try:
            # Validate artefact type
            if artefact_type not in self.FOLDER_MAPPING:
                logger.error(f"Unknown artefact type: {artefact_type}")
                return False

            # Generate filename for validation
            filename = self._generate_artefact_filename(artefact_type, **kwargs)

            # Validate naming conventions
            naming_validation = self.validate_artefact_naming_conventions(
                artefact_type, filename
            )
            if not naming_validation["valid"]:
                logger.warning(
                    f"Naming convention issues for {artefact_type}/{filename}: {naming_validation['issues']}"
                )
                # Don't fail, just warn - let the write proceed

            # Validate content
            if not self._validate_artefact_content(artefact_type, content):
                logger.error(
                    f"Content validation failed for artefact type: {artefact_type}"
                )
                return False

            # Validate artefact consistency
            consistency_validation = self.validate_artefact_consistency(
                artefact_type, content, filename
            )
            if not consistency_validation["consistent"]:
                logger.warning(
                    f"Consistency issues for {artefact_type}/{filename}: {consistency_validation['issues']}"
                )
                # Don't fail, just warn - let the write proceed

            # Ensure folder structure exists
            if not self.validate_folder_structure():
                logger.error("Failed to validate/ensure folder structure")
                return False

            # Handle different artefact types with enhanced error handling
            success = self._write_artefact_by_type(
                artefact_type, content, filename, **kwargs
            )

            if success:
                # Track metadata on successful write
                self.track_artefact_metadata(
                    artefact_type,
                    filename,
                    {
                        "naming_conventions": naming_validation["conventions_applied"],
                        "consistency_check": consistency_validation["consistent"],
                        "cross_references": consistency_validation["cross_references"],
                        "content_hash": hash(content),  # Basic content tracking
                    },
                )

                logger.info(
                    f"Successfully wrote artefact {artefact_type}/{filename} with comprehensive validation"
                )

            return success

        except Exception as e:
            logger.error(f"Failed to write artefact {artefact_type}: {e}")
            return False

    def _generate_artefact_filename(self, artefact_type: str, **kwargs) -> str:
        """Generate artefact filename based on type and parameters.

        Args:
            artefact_type: Type of artefact
            **kwargs: Parameters for filename generation

        Returns:
            str: Generated filename
        """
        try:
            if artefact_type == "stories":
                epic_num = kwargs.get("epic_num", 1)
                story_num = kwargs.get("story_num", 1)
                story_title = kwargs.get("story_title", "untitled")
                title_short = self._create_filename_slug(story_title)
                return f"{epic_num}.{story_num}.{title_short}.story.md"

            elif artefact_type == "qa_gates":
                epic_num = kwargs.get("epic_num", 1)
                story_num = kwargs.get("story_num", 1)
                story_slug = kwargs.get("story_slug", "unknown")
                return f"{epic_num}.{story_num}-{story_slug}.yml"

            elif artefact_type == "qa_assessments":
                epic_num = kwargs.get("epic_num", 1)
                story_num = kwargs.get("story_num", 1)
                assessment_type = kwargs.get("assessment_type", "unknown")
                date_str = datetime.now().strftime("%Y%m%d")
                return f"{epic_num}.{story_num}-{assessment_type}-{date_str}.md"

            elif artefact_type == "epics":
                epic_num = kwargs.get("epic_num", 1)
                epic_title = kwargs.get("epic_title", "untitled")
                title_short = self._create_filename_slug(epic_title)
                return f"epic-{epic_num}-{title_short}.md"

            elif artefact_type == "prd":
                return kwargs.get("filename", "prd.md")

            else:
                # Generic filename for unsupported types
                return f"{artefact_type}-{datetime.now().strftime('%Y%m%d')}.md"

        except Exception as e:
            logger.warning(f"Error generating filename for {artefact_type}: {e}")
            return f"{artefact_type}-unknown.md"

    def _write_artefact_by_type(
        self, artefact_type: str, content: str, filename: str, **kwargs
    ) -> bool:
        """Write artefact based on its type with appropriate method calls.

        Args:
            artefact_type: Type of artefact
            content: Artefact content
            filename: Generated filename
            **kwargs: Additional parameters

        Returns:
            bool: True if successful
        """
        try:
            # Handle different artefact types
            if artefact_type == "prd":
                return self.write_prd(content, filename)
            elif artefact_type == "stories":
                # Extract parameters from filename for story writing
                parts = filename.replace(".story.md", "").split(".")
                if len(parts) >= 3:
                    epic_num = int(parts[0])
                    story_num = int(parts[1])
                    story_title = ".".join(parts[2:])  # Reconstruct title
                    return self.write_story(content, epic_num, story_num, story_title)
                else:
                    logger.error(f"Invalid story filename format: {filename}")
                    return False
            elif artefact_type == "qa_gates":
                # Extract parameters from YAML filename
                parts = filename.replace(".yml", "").split("-", 1)
                if len(parts) >= 1:
                    epic_story = parts[0].split(".")
                    if len(epic_story) >= 2:
                        epic_num = int(epic_story[0])
                        story_num = int(epic_story[1])
                        story_slug = parts[1] if len(parts) > 1 else "unknown"
                        return self.write_quality_gate(
                            content, epic_num, story_num, story_slug
                        )
                logger.error(f"Invalid gate filename format: {filename}")
                return False
            elif artefact_type == "qa_assessments":
                # Extract parameters from assessment filename
                parts = filename.replace(".md", "").split("-")
                if len(parts) >= 3:
                    epic_story = parts[0].split(".")
                    if len(epic_story) >= 2:
                        epic_num = int(epic_story[0])
                        story_num = int(epic_story[1])
                        assessment_type = parts[1]
                        return self.write_assessment(
                            content, epic_num, story_num, assessment_type
                        )
                logger.error(f"Invalid assessment filename format: {filename}")
                return False
            elif artefact_type == "epics":
                # Extract parameters from epic filename
                if filename.startswith("epic-"):
                    parts = filename.replace(".md", "").split("-", 2)
                    if len(parts) >= 3:
                        epic_num = int(parts[1])
                        epic_title = parts[2]
                        return self.write_epic(content, epic_num, epic_title)
                logger.error(f"Invalid epic filename format: {filename}")
                return False
            else:
                # Generic file writing for unsupported types
                base_path = self.base_path / self.FOLDER_MAPPING[artefact_type]
                if str(base_path).endswith("/"):
                    # Directory path
                    full_path = base_path / filename
                else:
                    # File path
                    full_path = base_path

                return self._write_file(full_path, content)

        except Exception as e:
            logger.error(f"Error writing artefact by type {artefact_type}: {e}")
            return False

    def _validate_artefact_content(self, artefact_type: str, content) -> bool:
        """Validate artefact content before writing.

        Args:
            artefact_type: Type of artefact being validated
            content: Content to validate (string or dict for YAML)

        Returns:
            bool: True if content is valid
        """
        try:
            # Basic validation - content should not be empty
            if content is None:
                logger.error(f"Empty content for artefact type: {artefact_type}")
                return False

            # Handle string content
            if isinstance(content, str):
                if not content.strip():
                    logger.error(
                        f"Empty string content for artefact type: {artefact_type}"
                    )
                    return False

                # Type-specific validation for string content
                if artefact_type == "prd":
                    # PRD should contain basic structure
                    if not any(
                        header in content.lower()
                        for header in ["# prd", "# product", "product requirements"]
                    ):
                        logger.warning("PRD content may not contain expected structure")
                        # Don't fail, just warn

                elif artefact_type in ["stories", "epics"]:
                    # Stories/epics should have basic markdown structure
                    if not ("#" in content and "##" in content):
                        logger.warning(
                            f"{artefact_type} content may not contain expected markdown structure"
                        )
                        # Don't fail, just warn

                elif artefact_type == "qa_assessments":
                    # QA assessments should have markdown structure
                    if not ("#" in content):
                        logger.warning(
                            "QA assessment content may not contain expected markdown structure"
                        )

            # Handle dict content (for YAML artefacts like qa_gates)
            elif isinstance(content, dict):
                if not content:
                    logger.error(
                        f"Empty dict content for artefact type: {artefact_type}"
                    )
                    return False

                if artefact_type == "qa_gates":
                    # QA gates should have required fields
                    required_fields = ["schema", "story", "gate"]
                    missing_fields = [
                        field for field in required_fields if field not in content
                    ]
                    if missing_fields:
                        logger.warning(
                            f"QA gate content missing required fields: {missing_fields}"
                        )
                        # Don't fail, just warn

            else:
                logger.error(
                    f"Unsupported content type for {artefact_type}: {type(content)}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Content validation failed for {artefact_type}: {e}")
            return False
