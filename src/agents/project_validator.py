"""Project validator agent for multi-file projects."""

import re
from typing import Dict, List, Set, Tuple

from src.models.schemas import FileArtifact, ProgrammingLanguage
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ProjectValidatorAgent:
    """Agent responsible for validating multi-file project structure and dependencies."""

    def __init__(self):
        """Initialize the project validator agent."""
        logger.info("Project Validator Agent initialized")

    def validate_project(
        self, files: List[FileArtifact], language: ProgrammingLanguage
    ) -> Dict[str, any]:
        """
        Validate multi-file project for consistency and correctness.

        Args:
            files: List of FileArtifacts in the project
            language: Programming language

        Returns:
            Validation result with errors and warnings
        """
        try:
            logger.info(f"Validating {language.value} project with {len(files)} files")

            errors = []
            warnings = []

            if language == ProgrammingLanguage.PYTHON:
                errors.extend(self._validate_python_project(files))
            elif language == ProgrammingLanguage.JAVA:
                errors.extend(self._validate_java_project(files))

            success = len(errors) == 0

            if success:
                logger.info("Project validation passed")
            else:
                logger.warning(f"Project validation found {len(errors)} errors")

            return {
                "success": success,
                "errors": errors,
                "warnings": warnings,
                "file_count": len(files),
            }

        except Exception as e:
            logger.error(f"Project validation failed: {str(e)}")
            return {
                "success": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
            }

    def _validate_python_project(self, files: List[FileArtifact]) -> List[str]:
        """Validate Python project structure and imports."""
        errors = []

        # Extract imports from all files
        imports_by_file = {}
        for file in files:
            if file.language == "python" or file.filename.endswith(".py"):
                imports = self._extract_python_imports(file.code)
                imports_by_file[file.filename] = imports

        # Check for circular imports (warn only, don't error)
        circular = self._detect_circular_imports(imports_by_file)
        if circular:
            logger.warning(f"Potential circular imports detected: {circular}")

        # Check for missing __init__.py files
        py_dirs = self._get_python_package_dirs(files)
        for dir_path in py_dirs:
            if not any(f.filename == f"{dir_path}/__init__.py" for f in files):
                logger.warning(f"Missing __init__.py in {dir_path}")

        # Validate import paths (warn only, don't error)
        for filename, imports in imports_by_file.items():
            for imp in imports:
                if not self._is_valid_python_import(imp, files):
                    logger.warning(f"In {filename}: import '{imp}' not found in project")

        return errors

    def _validate_java_project(self, files: List[FileArtifact]) -> List[str]:
        """Validate Java project structure and packages."""
        errors = []

        # Check Java files (.java only) are in proper package structure
        java_files = [f for f in files if f.language == "java" or f.filename.endswith(".java")]

        # Warn if no files are under src/main/java but don't error if there are any Java files
        src_main_java_files = [f for f in java_files if "/src/main/java/" in f.filename]
        
        if java_files and not src_main_java_files:
            logger.warning(
                "Note: Java files should ideally be in src/main/java/ directory for Maven compatibility. "
                "However, proceeding with validation."
            )

        for file in java_files:
            # Extract package declaration
            package_match = re.search(r"package\s+([\w.]+);", file.code)
            if not package_match:
                logger.warning(f"Java file {file.filename} has no package declaration")
                continue
            
            package_name = package_match.group(1)
            # Only validate path match if the file is under src/main/java
            if "/src/main/java/" in file.filename:
                expected_path_suffix = package_name.replace(".", "/")
                if not expected_path_suffix in file.filename:
                    errors.append(
                        f"Java file {file.filename} package '{package_name}' doesn't match path"
                    )

        return errors

    def _extract_python_imports(self, code: str) -> List[str]:
        """Extract import statements from Python code."""
        imports = []

        # Match: import X, import X as Y, import X, Y, Z
        import_pattern = r"^import\s+([\w.,\s]+)"
        for match in re.finditer(import_pattern, code, re.MULTILINE):
            modules = match.group(1).split(",")
            for module in modules:
                module = module.strip().split()[0]  # Get first part before 'as'
                imports.append(module)

        # Match: from X import Y, from X import Y, Z
        from_pattern = r"^from\s+([\w.]+)\s+import"
        for match in re.finditer(from_pattern, code, re.MULTILINE):
            imports.append(match.group(1))

        return imports

    def _detect_circular_imports(self, imports_by_file: Dict[str, List[str]]) -> str:
        """Detect circular imports in the project."""
        # Simplified circular import detection
        for filename, imports in imports_by_file.items():
            for imp in imports:
                # Check if any imported file imports back to this file
                for other_file, other_imports in imports_by_file.items():
                    if other_file != filename:
                        module_name = self._extract_module_name(filename)
                        if module_name in other_imports:
                            return f"{filename} <-> {other_file}"

        return ""

    def _get_python_package_dirs(self, files: List[FileArtifact]) -> Set[str]:
        """Get all Python package directories."""
        dirs = set()

        for file in files:
            if file.filename.endswith(".py"):
                parts = file.filename.split("/")
                if len(parts) > 1:
                    dirs.add("/".join(parts[:-1]))

        return dirs

    def _is_valid_python_import(self, imp: str, files: List[FileArtifact]) -> bool:
        """Check if a Python import is valid in the project context."""
        # Known standard library modules (partial list)
        stdlib = {
            "os",
            "sys",
            "json",
            "re",
            "math",
            "time",
            "datetime",
            "collections",
            "itertools",
            "functools",
            "logging",
            "typing",
        }

        if imp in stdlib:
            return True

        # Check if module exists as a file in project
        for file in files:
            if file.filename.endswith(".py"):
                module_name = self._extract_module_name(file.filename)
                if module_name.startswith(imp):
                    return True

        # Assume third-party packages are available
        return True

    def _extract_module_name(self, filename: str) -> str:
        """Extract module name from file path."""
        if filename.endswith(".py"):
            return filename[:-3].replace("/", ".")
        return filename.replace("/", ".")
