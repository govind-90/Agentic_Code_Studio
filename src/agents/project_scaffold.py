"""Project scaffolding agent for multi-file projects."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config.project_templates import PROJECT_TEMPLATES, get_template
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ProjectScaffoldAgent:
    """Agent responsible for scaffolding multi-file project structures."""

    def __init__(self):
        """Initialize the project scaffold agent."""
        logger.info("Project Scaffold Agent initialized")

    def scaffold_project(
        self, project_name: str, template_name: str, root_dir: Path
    ) -> Dict[str, any]:
        """
        Scaffold a new project with the given template.

        Args:
            project_name: Name of the project
            template_name: Template to use (fastapi, spring_boot, python_package)
            root_dir: Root directory where project will be created

        Returns:
            Dict with status, file list, and directory structure
        """
        try:
            logger.info(
                f"Scaffolding project '{project_name}' with template '{template_name}'"
            )

            template = get_template(template_name)
            if not template:
                return {
                    "success": False,
                    "error": f"Template '{template_name}' not found",
                }

            # Handle None root_dir
            if root_dir is None:
                from src.config.settings import settings
                root_dir = Path(settings.get_project_root()) / "outputs" / "generated_code"
            else:
                root_dir = Path(root_dir)

            project_root = root_dir / project_name
            project_root.mkdir(parents=True, exist_ok=True)

            # Create directory structure
            dir_structure = self._create_directory_structure(
                project_root, template.get("structure", {})
            )

            # Create config files
            config_files = self._create_config_files(
                project_root,
                template.get("config_files", {}),
                project_name,
            )

            # Generate file manifest
            all_files = dir_structure + config_files
            file_tree = self._build_file_tree(project_root)

            logger.info(
                f"Project scaffolded successfully. Created {len(all_files)} files."
            )

            return {
                "success": True,
                "project_root": str(project_root),
                "files": all_files,
                "file_tree": file_tree,
                "template": template_name,
                "file_count": len(all_files),
            }

        except Exception as e:
            logger.error(f"Project scaffolding failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _create_directory_structure(
        self, root: Path, structure: Dict, parent_path: str = ""
    ) -> List[str]:
        """
        Create directory structure from template.

        Args:
            root: Root directory path
            structure: Nested dict defining structure
            parent_path: Current path for tracking

        Returns:
            List of created file/directory paths
        """
        created = []

        for name, content in structure.items():
            current_path = Path(parent_path) / name if parent_path else Path(name)
            full_path = root / current_path

            if isinstance(content, dict):
                # It's a directory
                full_path.mkdir(parents=True, exist_ok=True)
                created.append(str(current_path))
                logger.info(f"Created directory: {current_path}")

                # Recursively create subdirectories
                sub_created = self._create_directory_structure(
                    root, content, str(current_path)
                )
                created.extend(sub_created)
            else:
                # It's a file
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content or "")
                created.append(str(current_path))
                logger.info(f"Created file: {current_path}")

        return created

    def _create_config_files(
        self, root: Path, config_files: Dict[str, str], project_name: str
    ) -> List[str]:
        """
        Create configuration files.

        Args:
            root: Root directory path
            config_files: Dict of {filename: content}
            project_name: Project name for substitution

        Returns:
            List of created config file paths
        """
        created = []

        for filename, content in config_files.items():
            file_path = root / filename

            # Substitute project name where needed
            content = content.replace("mypackage", project_name)
            content = content.replace("my-package", project_name.replace("_", "-"))
            content = content.replace(
                "com.example", f"com.{project_name.replace('-', '')}"
            )

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            created.append(filename)
            logger.info(f"Created config file: {filename}")

        return created

    def _build_file_tree(self, root: Path, prefix: str = "") -> Dict[str, any]:
        """
        Build a file tree representation.

        Args:
            root: Root directory
            prefix: Path prefix for tree building

        Returns:
            Nested dict representing file tree
        """
        tree = {}

        try:
            for item in sorted(root.iterdir()):
                if item.name.startswith(".") and item.name != ".gitignore":
                    continue

                rel_path = item.relative_to(root)
                key = item.name

                if item.is_dir():
                    tree[key] = self._build_file_tree(item, str(rel_path))
                else:
                    tree[key] = {
                        "type": "file",
                        "size": item.stat().st_size,
                        "path": str(rel_path),
                    }
        except Exception as e:
            logger.warning(f"Error building file tree: {e}")

        return tree

    def get_template_info(self, template_name: str) -> Dict[str, any]:
        """Get template information and metadata."""
        template = get_template(template_name)
        if not template:
            return {"success": False, "error": f"Template '{template_name}' not found"}
            # Use provided root_dir or default to outputs/generated_code
            if root_dir is None:
                from src.config.settings import settings
                root_dir = str(Path(settings.session_storage_path).parent / "generated_code")

            project_root = Path(root_dir) / project_name
            project_root.mkdir(parents=True, exist_ok=True)

        return {
            "success": True,
            "name": template.get("name"),
            "description": template.get("description"),
            "language": template.get("language"),
            "files": len(template.get("config_files", {})),
        }
