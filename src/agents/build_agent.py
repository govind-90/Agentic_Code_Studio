"""Build and compilation agent."""

import ast
import json
import subprocess
from typing import Dict

from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.prompts import BUILD_AGENT_HUMAN_TEMPLATE, BUILD_AGENT_SYSTEM_PROMPT
from src.config.settings import settings
from src.models.schemas import BuildResult, ProgrammingLanguage
from src.tools.code_executor import install_python_dependencies
from src.utils.logger import build_logger as logger


class BuildAgent:
    """Agent responsible for building and validating code."""

    def __init__(self):
        """Initialize the build agent."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=settings.google_api_key,
            temperature=settings.agent_temperature,
            convert_system_message_to_human=True,
        )

        logger.info("Build Agent initialized")

    def analyze_and_build(
        self, code: str, language: ProgrammingLanguage, dependencies: list
    ) -> BuildResult:
        """
        Analyze code and prepare for execution.

        Args:
            code: Generated code
            language: Programming language
            dependencies: List of dependencies

        Returns:
            BuildResult with status and details
        """
        try:
            logger.info(f"Analyzing {language.value} code for build")

            if language == ProgrammingLanguage.PYTHON:
                return self._build_python(code, dependencies)
            elif language == ProgrammingLanguage.JAVA:
                return self._build_java(code, dependencies)
            else:
                return BuildResult(
                    status="error", errors=[f"Unsupported language: {language}"]
                )

        except Exception as e:
            logger.error(f"Build analysis failed: {str(e)}")
            return BuildResult(status="error", errors=[str(e)])

    def _build_python(self, code: str, dependencies: list) -> BuildResult:
        """Build Python code."""
        errors = []
        suggested_fixes = []

        # 1. Syntax validation
        try:
            ast.parse(code)
            logger.info("Python syntax validation passed")
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            errors.append(error_msg)
            suggested_fixes.append(f"Fix syntax error: {e.msg}")
            logger.error(error_msg)

            return BuildResult(
                status="error",
                dependencies=dependencies,
                errors=errors,
                suggested_fixes=suggested_fixes,
                build_instructions="Fix syntax errors before proceeding",
            )

        # 2. Install dependencies
        if dependencies:
            logger.info(f"Installing Python dependencies: {dependencies}")
            install_result = install_python_dependencies.invoke(
                {"dependencies": dependencies}
            )

            if not install_result.get("success"):
                errors.append(
                    f"Failed to install dependencies: {install_result.get('stderr', '')}"
                )
                suggested_fixes.append("Check package names and network connectivity")

                return BuildResult(
                    status="error",
                    dependencies=dependencies,
                    errors=errors,
                    suggested_fixes=suggested_fixes,
                    build_instructions="Resolve dependency installation issues",
                )

        # 3. Success
        logger.info("Python build completed successfully")
        return BuildResult(
            status="success",
            dependencies=dependencies,
            build_instructions="Code is ready for execution",
            suggested_fixes=[],
        )

    def _build_java(self, code: str, dependencies: list) -> BuildResult:
        """Build Java code with Maven."""
        import tempfile
        from pathlib import Path

        errors = []
        suggested_fixes = []

        try:
            # Create temporary Maven project
            temp_dir = Path(tempfile.mkdtemp())

            # Extract class name and package
            import re

            package_match = re.search(r"package\s+([\w.]+);", code)
            package_name = package_match.group(1) if package_match else None

            class_match = re.search(r"public\s+class\s+(\w+)", code)
            if not class_match:
                return BuildResult(
                    status="error",
                    errors=["Could not find public class declaration"],
                    suggested_fixes=["Ensure code has 'public class ClassName'"],
                )

            class_name = class_match.group(1)

            # Extract additional dependencies from imports
            detected_deps = self._detect_java_dependencies(code)

            # Normalize dependencies: produce pom_deps (list[dict]) and
            # result_deps (list[str] in 'group:artifact:version' form)
            pom_deps = []
            result_deps = []

            def _add_pom_dep(dep_dict):
                key = (
                    dep_dict.get("groupId"),
                    dep_dict.get("artifactId"),
                    dep_dict.get("version"),
                )
                existing_keys = {
                    (d.get("groupId"), d.get("artifactId"), d.get("version"))
                    for d in pom_deps
                }
                if key not in existing_keys:
                    pom_deps.append(dep_dict)

            # Process provided dependencies (strings "g:a:v" or dicts)
            for d in dependencies or []:
                if isinstance(d, dict):
                    _add_pom_dep(d)
                    coord = f"{d['groupId']}:{d['artifactId']}:{d['version']}"
                    if coord not in result_deps:
                        result_deps.append(coord)
                elif isinstance(d, str):
                    parts = d.split(":")
                    if len(parts) == 3:
                        dep_dict = {"groupId": parts[0], "artifactId": parts[1], "version": parts[2]}
                        _add_pom_dep(dep_dict)
                        if d not in result_deps:
                            result_deps.append(d)

            # Add auto-detected deps (they are dicts)
            for dd in detected_deps:
                if isinstance(dd, dict):
                    _add_pom_dep(dd)
                    coord = f"{dd['groupId']}:{dd['artifactId']}:{dd['version']}"
                    if coord not in result_deps:
                        result_deps.append(coord)

            logger.info(f"Detected dependencies (pom): {pom_deps}")
            logger.info(f"Dependencies (result): {result_deps}")

            # Create Maven structure
            if package_name:
                package_path = package_name.replace(".", "/")
                src_dir = temp_dir / "src" / "main" / "java" / package_path
            else:
                src_dir = temp_dir / "src" / "main" / "java"

            src_dir.mkdir(parents=True, exist_ok=True)

            java_file = src_dir / f"{class_name}.java"
            java_file.write_text(code)

            # Create pom.xml with detected dependencies (use dicts for pom)
            pom_content = self._generate_pom_xml(class_name, pom_deps, package_name)
            (temp_dir / "pom.xml").write_text(pom_content)

            logger.info(f"Created Maven project in {temp_dir}")

            # Ensure Maven is available before attempting to run
            import shutil
            import platform

            mvn_path = shutil.which("mvn")
            
            # If not in PATH, check common Windows installation locations
            if not mvn_path and platform.system() == "Windows":
                common_paths = [
                    Path("C:/Program Files/apache-maven-3.9.11/bin/mvn.cmd"),
                    Path("C:/Program Files/apache-maven-3.9.10/bin/mvn.cmd"),
                    Path("C:/Program Files/apache-maven-3.9.9/bin/mvn.cmd"),
                    Path("C:/Program Files/apache-maven-3.9.8/bin/mvn.cmd"),
                    Path("C:/Program Files/apache-maven-3.8.8/bin/mvn.cmd"),
                    Path("C:/Program Files/apache-maven-3.8.7/bin/mvn.cmd"),
                ]
                for candidate in common_paths:
                    if candidate.exists():
                        mvn_path = str(candidate)
                        logger.info(f"Found Maven at: {mvn_path}")
                        break

            # Look for mvnw or mvnw.cmd in repo root as a fallback
            mvnw_path = None
            repo_root = Path(__file__).parent.parent.parent
            for candidate in (repo_root / "mvnw", repo_root / "mvnw.cmd", temp_dir / "mvnw", temp_dir / "mvnw.cmd"):
                if candidate.exists():
                    mvnw_path = str(candidate)
                    break

            if not mvn_path and not mvnw_path:
                # Provide a helpful message for Windows users as well
                return BuildResult(
                    status="error",
                    errors=["Maven (mvn) not found in system PATH or common installation locations"],
                    suggested_fixes=[
                        "Maven is installed but not in PATH. Please:",
                        "1. Add Maven bin directory to system PATH: C:\\Program Files\\apache-maven-3.9.11\\bin",
                        "2. Then restart VS Code to refresh the environment",
                        "Or add a Maven wrapper (mvnw) to the project",
                    ],
                )

            cmd = mvn_path if mvn_path else mvnw_path
            # Build command with proper quoting for Windows paths with spaces
            if platform.system() == "Windows":
                run_cmd = f'"{cmd}" clean compile'
            else:
                run_cmd = "mvn clean compile" if mvn_path and not "/" in mvn_path else f"{cmd} clean compile"

            compile_result = subprocess.run(
                run_cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
                shell=True,
            )

            if compile_result.returncode != 0:
                # Parse Java compilation errors
                logger.error(f"Maven compilation failed with return code {compile_result.returncode}")
                logger.error(f"Maven stdout: {compile_result.stdout}")
                logger.error(f"Maven stderr: {compile_result.stderr}")
                
                parsed_errors = self._parse_java_errors(compile_result.stderr)
                errors.extend(parsed_errors["errors"])
                suggested_fixes.extend(parsed_errors["fixes"])

                logger.error("Maven compilation failed")

                return BuildResult(
                    status="error",
                    dependencies=result_deps,
                    errors=errors,
                    suggested_fixes=suggested_fixes,
                    build_instructions="Fix compilation errors",
                )

            logger.info("Java build completed successfully")

            # Clean up
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

            return BuildResult(
                status="success",
                dependencies=result_deps,
                build_instructions=f"Java class {class_name} compiled successfully",
                suggested_fixes=[],
            )

        except subprocess.TimeoutExpired:
            return BuildResult(
                status="error",
                errors=["Maven build timed out"],
                suggested_fixes=["Simplify dependencies or increase timeout"],
            )
        except FileNotFoundError:
            return BuildResult(
                status="error",
                errors=["Maven (mvn) not found in system PATH"],
                suggested_fixes=[
                    "Install Maven: sudo apt install maven (Linux) or brew install maven (macOS)"
                ],
            )
        except Exception as e:
            logger.error(f"Java build error: {str(e)}")
            return BuildResult(
                status="error",
                errors=[str(e)],
                suggested_fixes=["Review Java code structure and syntax"],
            )

    def _detect_java_dependencies(self, code: str) -> list:
        """Auto-detect Java dependencies from imports."""
        import re

        dependencies = []
        imports = re.findall(r"^import\s+([\w.]+);", code, re.MULTILINE)

        # Dependency mapping: import prefix -> Maven artifact
        dependency_map = {
            "com.google.gson": {
                "groupId": "com.google.code.gson",
                "artifactId": "gson",
                "version": "2.10.1",
            },
            "org.apache.http": {
                "groupId": "org.apache.httpcomponents",
                "artifactId": "httpclient",
                "version": "4.5.14",
            },
            "org.apache.commons.lang3": {
                "groupId": "org.apache.commons",
                "artifactId": "commons-lang3",
                "version": "3.14.0",
            },
            "org.json": {
                "groupId": "org.json",
                "artifactId": "json",
                "version": "20231013",
            },
            "com.fasterxml.jackson": {
                "groupId": "com.fasterxml.jackson.core",
                "artifactId": "jackson-databind",
                "version": "2.16.0",
            },
            "org.slf4j": {
                "groupId": "org.slf4j",
                "artifactId": "slf4j-simple",
                "version": "2.0.9",
            },
        }

        for imp in imports:
            # Skip standard Java imports
            if imp.startswith("java.") or imp.startswith("javax."):
                continue

            # Check against known dependencies
            for prefix, dep_info in dependency_map.items():
                if imp.startswith(prefix):
                    dependencies.append(dep_info)
                    break

        return dependencies

    def _parse_java_errors(self, error_output: str) -> dict:
        """Parse Java compilation errors and provide actionable fixes."""

        import re

        errors = []
        fixes = []

        # Pattern: filename.java:[line]: error: message
        error_pattern = re.compile(r"(\w+\.java):(\d+):\s*error:\s*(.+)")

        matches = error_pattern.findall(error_output)
        for filename, line, message in matches:
            errors.append(f"{filename}:{line} - {message}")

        # Specific error patterns and fixes
        if "cannot find symbol" in error_output:
            fixes.append("Missing import statement or undefined variable")
            fixes.append("Check if all classes and methods are properly imported")

        if "class, interface, or enum expected" in error_output:
            fixes.append("Invalid class structure - ensure proper class declaration")

        if "incompatible types" in error_output:
            fixes.append("Type mismatch - check variable types and method return types")

        if "method does not override" in error_output:
            fixes.append(
                "Remove @Override annotation or implement the correct method signature"
            )

        if "unreachable statement" in error_output:
            fixes.append("Remove code after return/throw statements")

        if "variable might not have been initialized" in error_output:
            fixes.append("Initialize variables before use")

        if (
            "package does not exist" in error_output
            or "cannot find symbol" in error_output
        ):
            fixes.append("Add required Maven dependencies to pom.xml")
            fixes.append("Ensure all external libraries are properly declared")

        # If no specific errors found, add generic error
        if not errors:
            errors.append(error_output[:500])  # First 500 chars of error

        if not fixes:
            fixes.append("Review Java syntax and structure")
            fixes.append("Check Maven dependencies")

        return {"errors": errors, "fixes": fixes}

    def _generate_pom_xml(
        self, main_class: str, dependencies: list, package_name: str = None
    ) -> str:
        """Generate Maven pom.xml."""
        # Basic pom.xml template
        pom = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.agenticcode</groupId>
    <artifactId>generated-project</artifactId>
    <version>1.0-SNAPSHOT</version>
    
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    
    <dependencies>
"""

        # Parse and add dependencies
        for dep in dependencies:
            if isinstance(dep, dict):
                # If it's a dict (from detected_deps)
                pom += f"""        <dependency>
            <groupId>{dep['groupId']}</groupId>
            <artifactId>{dep['artifactId']}</artifactId>
            <version>{dep['version']}</version>
        </dependency>
"""
            elif isinstance(dep, str):
                # If it's a string in format "groupId:artifactId:version"
                parts = dep.split(":")
                if len(parts) == 3:
                    pom += f"""        <dependency>
            <groupId>{parts[0]}</groupId>
            <artifactId>{parts[1]}</artifactId>
            <version>{parts[2]}</version>
        </dependency>
"""

        pom += """    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
            </plugin>
            <plugin>
                <groupId>org.codehaus.mojo</groupId>
                <artifactId>exec-maven-plugin</artifactId>
                <version>3.1.0</version>
                <configuration>
                    <mainClass>{}</mainClass>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>""".format(
            main_class
        )

        return pom
