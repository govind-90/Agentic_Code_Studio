"""Build and compilation agent."""

import ast
import json
import subprocess
from typing import Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from src.config.prompts import BUILD_AGENT_HUMAN_TEMPLATE, BUILD_AGENT_SYSTEM_PROMPT
from src.config.settings import settings
from src.models.schemas import BuildResult, FileArtifact, ProgrammingLanguage
from src.tools.code_executor import install_python_dependencies
from src.utils.logger import build_logger as logger


class BuildAgent:
    """Agent responsible for building and validating code."""

    # def __init__(self):
    #     """Initialize the build agent."""
    #     self.llm = ChatGoogleGenerativeAI(
    #         model=settings.llm_model_name,
    #         google_api_key=settings.google_api_key,
    #         temperature=settings.agent_temperature,
    #         convert_system_message_to_human=True,
    #     )

    #     logger.info("Build Agent initialized")

    def __init__(self):
        """Initialize the build agent."""
        self.llm = ChatGroq(
            model=settings.llm_model_name_groq,
            groq_api_key=settings.groq_api_key,
            temperature=settings.agent_temperature,
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

    def build_project(
        self, files: list, language: ProgrammingLanguage, dependencies: list, root_dir: str = None
    ) -> BuildResult:
        """
        Build a multi-file project.

        Args:
            files: List of FileArtifact objects
            language: Programming language
            dependencies: List of project dependencies
            root_dir: Root directory of the project

        Returns:
            BuildResult with status and details
        """
        try:
            logger.info(f"Building multi-file {language.value} project with {len(files)} files")

            if language == ProgrammingLanguage.PYTHON:
                return self._build_python_project(files, dependencies, root_dir)
            elif language == ProgrammingLanguage.JAVA:
                return self._build_java_project(files, dependencies, root_dir)
            else:
                return BuildResult(
                    status="error", errors=[f"Unsupported language: {language}"]
                )

        except Exception as e:
            logger.error(f"Project build failed: {str(e)}")
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
            # Filter out project-internal modules and comments
            project_internals = {"src", "app", "tests", "test", "config", "utils", "models", 
                                "schemas", "database", "api", "core", "services", "controllers", 
                                "views", "main", "lib", "common"}
            
            # Filter out Python standard library modules
            stdlib_modules = {
                "logging", "typing", "json", "math", "itertools", "collections", "datetime", "re", "sys", "os",
                "unittest", "pathlib", "io", "subprocess", "tempfile", "shutil", "copy", "pickle",
                "threading", "multiprocessing", "argparse", "configparser", "email", "urllib", "http",
                "socket", "ssl", "asyncio", "hashlib", "hmac", "secrets", "uuid", "enum", "dataclasses",
                "abc", "time", "csv", "functools", "random", "string", "textwrap", "difflib", "warnings",
                "sqlite3", "dbm", "shelve"
            }
            
            filtered_deps = [
                d for d in dependencies 
                if d and str(d).strip() 
                and not str(d).strip().startswith("#")  # Filter comments
                and str(d).strip().lower() not in project_internals
                and str(d).strip().lower() not in stdlib_modules  # Filter stdlib
            ]
            
            if len(filtered_deps) < len(dependencies):
                removed = [d for d in dependencies if d not in filtered_deps]
                logger.warning(f"Filtered out project-internal modules: {removed}")
            
            logger.info(f"Installing Python dependencies: {filtered_deps}")
            install_result = install_python_dependencies.invoke(
                {"dependencies": filtered_deps}
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

            # Match public class, handling annotations (e.g., @RestController\npublic class...)
            class_match = re.search(r"public\s+class\s+(\w+)", code, re.MULTILINE)
            if not class_match:
                # Log first 500 chars of code for debugging
                logger.error(f"No public class found. Code preview: {code[:500]}")
                return BuildResult(
                    status="error",
                    errors=[
                        "Could not find public class declaration",
                        "The generated code may be incomplete or invalid Java"
                    ],
                    suggested_fixes=[
                        "Ensure code has 'public class ClassName'",
                        "Check that code is valid Java (not pseudocode or incomplete)",
                        "For Spring Boot single-file: Simplify the request or use multi-file generation"
                    ],
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

            # Check if this is a Spring Boot class and add essential starters
            has_spring = any(
                d.get("groupId", "").startswith("org.springframework") 
                for d in pom_deps
            )
            
            if has_spring:
                # Add essential Spring Boot starters if not already present
                essential_starters = [
                    ("org.springframework.boot", "spring-boot-starter-web", "3.1.5"),  # Always include web for REST APIs
                    ("org.springframework.boot", "spring-boot-starter-data-jpa", "3.1.5"),
                    ("org.springframework.boot", "spring-boot-starter-validation", "3.1.5"),
                ]
                
                # Check if security is used in the code
                if "Security" in code or "security" in code.lower():
                    essential_starters.append(
                        ("org.springframework.boot", "spring-boot-starter-security", "3.1.5")
                    )
                
                # Check if JWT is used
                if "jwt" in code.lower() or "Jwt" in code or "jsonwebtoken" in code.lower():
                    essential_starters.extend([
                        ("io.jsonwebtoken", "jjwt-api", "0.11.5"),
                        ("io.jsonwebtoken", "jjwt-impl", "0.11.5"),
                        ("io.jsonwebtoken", "jjwt-jackson", "0.11.5"),
                    ])
                
                for group, artifact, version in essential_starters:
                    dep_dict = {"groupId": group, "artifactId": artifact, "version": version}
                    coord = (group, artifact, version)
                    existing_keys = {
                        (d.get("groupId"), d.get("artifactId"), d.get("version"))
                        for d in pom_deps
                    }
                    if coord not in existing_keys:
                        pom_deps.append(dep_dict)
                        result_deps.append(f"{group}:{artifact}:{version}")
                        logger.info(f"Added essential Spring Boot starter: {artifact}")

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
                # Parse Java compilation errors from both stdout and stderr
                logger.error(f"Maven compilation failed with return code {compile_result.returncode}")
                logger.error(f"Maven stdout: {compile_result.stdout}")
                logger.error(f"Maven stderr: {compile_result.stderr}")
                
                # Maven outputs errors to both stdout and stderr, check both
                error_output = compile_result.stderr + "\n" + compile_result.stdout
                parsed_errors = self._parse_java_errors(error_output)
                errors.extend(parsed_errors["errors"])
                suggested_fixes.extend(parsed_errors["fixes"])
                
                # Also include relevant Maven output for better context
                if "[ERROR]" in compile_result.stdout:
                    maven_errors = [line for line in compile_result.stdout.split('\n') if '[ERROR]' in line]
                    errors.extend(maven_errors[:5])  # First 5 Maven error lines

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
            "org.springframework": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-web",
                "version": "3.1.5",
            },
            "org.springframework.security": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-security",
                "version": "3.1.5",
            },
            "org.springframework.security.authentication": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-security",
                "version": "3.1.5",
            },
            "org.springframework.security.config": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-security",
                "version": "3.1.5",
            },
            "org.springframework.security.crypto": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-security",
                "version": "3.1.5",
            },
            "org.springframework.data.jpa": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-data-jpa",
                "version": "3.1.5",
            },
            "com.mysql": {
                "groupId": "org.mariadb.jdbc",
                "artifactId": "mariadb-java-client",
                "version": "3.1.4",
            },
            "mysql": {
                "groupId": "org.mariadb.jdbc",
                "artifactId": "mariadb-java-client",
                "version": "3.1.4",
            },
            "org.springframework.web": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-web",
                "version": "3.1.5",
            },
            "org.springframework.http": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-web",
                "version": "3.1.5",
            },
            "jakarta.persistence": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-data-jpa",
                "version": "3.1.5",
            },
            "jakarta.validation": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-validation",
                "version": "3.1.5",
            },
            "javax.validation": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-validation",
                "version": "3.1.5",
            },
            "jakarta.": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-web",
                "version": "3.1.5",
            },
            "org.springframework.boot.actuate": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-actuator",
                "version": "3.1.5",
            },
            "lombok": {
                "groupId": "org.projectlombok",
                "artifactId": "lombok",
                "version": "1.18.26",
            },
            "io.jsonwebtoken": {
                "groupId": "io.jsonwebtoken",
                "artifactId": "jjwt-api",
                "version": "0.11.5",
            },
            "org.junit": {
                "groupId": "org.junit.jupiter",
                "artifactId": "junit-jupiter-api",
                "version": "5.10.0",
            },
            "org.mockito": {
                "groupId": "org.mockito",
                "artifactId": "mockito-core",
                "version": "5.5.0",
            },
            "org.springframework.boot": {
                "groupId": "org.springframework.boot",
                "artifactId": "spring-boot-starter-web",
                "version": "3.1.5",
            },
            "org.slf4j": {
                "groupId": "org.slf4j",
                "artifactId": "slf4j-simple",
                "version": "2.0.9",
            },
            "io.swagger.v3.oas": {
                "groupId": "org.springdoc",
                "artifactId": "springdoc-openapi-starter-webmvc-ui",
                "version": "2.2.0",
            },
            "org.springdoc": {
                "groupId": "org.springdoc",
                "artifactId": "springdoc-openapi-starter-webmvc-ui",
                "version": "2.2.0",
            },
            "jakarta.enterprise.context": {
                "groupId": "jakarta.enterprise",
                "artifactId": "jakarta.enterprise.cdi-api",
                "version": "4.0.1",
            },
            "jakarta.enterprise.inject": {
                "groupId": "jakarta.enterprise",
                "artifactId": "jakarta.enterprise.cdi-api",
                "version": "4.0.1",
            },
            "jakarta.inject": {
                "groupId": "jakarta.inject",
                "artifactId": "jakarta.inject-api",
                "version": "2.0.1",
            },
            "org.apache.commons.dbcp2": {
                "groupId": "org.apache.commons",
                "artifactId": "commons-dbcp2",
                "version": "2.11.0",
            },
        }

        for imp in imports:
            # Skip standard Java imports (but not jakarta.* - those need external deps)
            if imp.startswith("java."):
                continue
            # Skip javax.sql and javax.naming (JDK built-ins)
            if imp.startswith("javax.sql") or imp.startswith("javax.naming"):
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
        # Add detection for Spring Boot related dependencies
        spring_present = any(
            (isinstance(d, dict) and str(d.get("groupId", "")).startswith("org.springframework"))
            or (isinstance(d, str) and str(d).startswith("org.springframework"))
            for d in (dependencies or [])
        )

        # Basic pom.xml header
        pom = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.agenticcode</groupId>
    <artifactId>generated-project</artifactId>
    <version>1.0-SNAPSHOT</version>
"""

        # If Spring Boot deps detected, add parent
        if spring_present:
            pom += """
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.1.5</version>
        <relativePath/> <!-- lookup parent from repository -->
    </parent>
"""

        pom += """
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
"""

        # Add Spring Boot Maven plugin if spring detected
        if spring_present:
            pom += """
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
"""

        # Always include compiler and exec plugin
        pom += f"""
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
                    <mainClass>{main_class}</mainClass>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
"""

        return pom

    def _build_python_project(
        self, files: list, dependencies: list, root_dir: str = None
    ) -> BuildResult:
        """Build a multi-file Python project."""
        import ast

        errors = []
        suggested_fixes = []

        # 1. Validate syntax of all Python files
        python_files = [f for f in files if f.language == "python" and f.filename.endswith('.py')]
        logger.info(f"Validating {len(python_files)} Python files")

        for file in python_files:
            try:
                ast.parse(file.code)
                logger.info(f"✓ Syntax valid: {file.filename}")
            except SyntaxError as e:
                error_msg = f"{file.filename}:{e.lineno} - {e.msg}"
                errors.append(error_msg)
                suggested_fixes.append(f"Fix syntax in {file.filename}")
                logger.error(error_msg)

        if errors:
            return BuildResult(
                status="error",
                errors=errors,
                suggested_fixes=suggested_fixes,
                build_instructions="Fix syntax errors in all files",
            )

        # 2. Install all dependencies
        if dependencies:
            # Filter out project-internal modules and comments (defensive filtering for old sessions)
            project_internals = {"src", "app", "tests", "test", "config", "utils", "models", 
                                "schemas", "database", "api", "core", "services", "controllers", 
                                "views", "main", "lib", "common"}
            
            # Filter out Python standard library modules
            stdlib_modules = {
                "logging", "typing", "json", "math", "itertools", "collections", "datetime", "re", "sys", "os",
                "unittest", "pathlib", "io", "subprocess", "tempfile", "shutil", "copy", "pickle",
                "threading", "multiprocessing", "argparse", "configparser", "email", "urllib", "http",
                "socket", "ssl", "asyncio", "hashlib", "hmac", "secrets", "uuid", "enum", "dataclasses",
                "abc", "time", "csv", "functools", "random", "string", "textwrap", "difflib", "warnings",
                "sqlite3", "dbm", "shelve"
            }
            
            filtered_deps = [
                d for d in dependencies 
                if d and str(d).strip()
                and not str(d).strip().startswith("#")  # Filter comments
                and str(d).strip().lower() not in project_internals
                and str(d).strip().lower() not in stdlib_modules  # Filter stdlib
            ]
            
            if len(filtered_deps) < len(dependencies):
                removed = [d for d in dependencies if d not in filtered_deps]
                logger.warning(f"Filtered out project-internal modules: {removed}")
            
            if not filtered_deps:
                logger.info("No external dependencies to install after filtering")
                return BuildResult(
                    status="success",
                    dependencies=[],
                    build_instructions="All files validated, no external dependencies needed",
                    suggested_fixes=[],
                )
            
            logger.info(f"Installing project dependencies: {filtered_deps}")
            install_result = install_python_dependencies.invoke(
                {"dependencies": filtered_deps}
            )

            if not install_result.get("success"):
                errors.append(
                    f"Failed to install dependencies: {install_result.get('stderr', '')}"
                )
                suggested_fixes.append("Check package names and versions")

                return BuildResult(
                    status="error",
                    errors=errors,
                    dependencies=dependencies,
                    suggested_fixes=suggested_fixes,
                    build_instructions="Resolve dependency issues",
                )

        logger.info("Python project build completed successfully")
        return BuildResult(
            status="success",
            dependencies=dependencies,
            build_instructions="All files validated and dependencies installed",
            suggested_fixes=[],
        )

    def _build_java_project(
        self, files: list, dependencies: list, root_dir: str = None
    ) -> BuildResult:
        """Build a multi-file Java project."""
        import tempfile
        from pathlib import Path
        import shutil
        import platform

        errors = []
        suggested_fixes = []

        try:
            # Create temp Maven project
            temp_dir = Path(tempfile.mkdtemp())
            logger.info(f"Creating Maven project in {temp_dir}")

            # Find main class (class with main method)
            main_class = None
            main_class_file = None
            # Filter to only .java files
            java_files = [f for f in files if f.filename.endswith(".java")]

            for file in java_files:
                if "public static void main" in file.code:
                    import re

                    match = re.search(r"public\s+class\s+(\w+)", file.code)
                    if match:
                        main_class = match.group(1)
                        main_class_file = file
                        break

            if not main_class_file and java_files:
                main_class_file = java_files[0]

            if not main_class_file:
                return BuildResult(
                    status="error",
                    errors=["No Java files found in project"],
                    suggested_fixes=["Add Java source files"],
                )

            # Create source directory structure
            src_main_dir = temp_dir / "src" / "main" / "java"
            src_test_dir = temp_dir / "src" / "test" / "java"

            for file in java_files:
                # Determine if this is a test file
                is_test_file = "Test" in file.filename or "/test/" in file.filename or "\\test\\" in file.filename
                import re

                # Choose correct base directory (main or test)
                base_src_dir = src_test_dir if is_test_file else src_main_dir

                # Extract package if present
                package_match = re.search(r"package\s+([\w.]+);", file.code)
                if package_match:
                    package_name = package_match.group(1)
                    package_path = package_name.replace(".", "/")
                    file_src_dir = base_src_dir / package_path
                else:
                    file_src_dir = base_src_dir

                file_src_dir.mkdir(parents=True, exist_ok=True)

                # Use the filename from the file object if available (respects LLM-generated names)
                # Otherwise extract the public type name (class, interface, enum, record)
                if file.filename and not file.filename.startswith("file_"):
                    # Use the original filename (strip path if present)
                    java_filename = file.filename.split('/')[-1]
                    if not java_filename.endswith('.java'):
                        java_filename += '.java'
                else:
                    # Fallback: extract public type name (class, interface, enum, record)
                    type_match = re.search(r"public\s+(?:class|interface|enum|record)\s+(\w+)", file.code)
                    type_name = type_match.group(1) if type_match else "Main"
                    java_filename = f"{type_name}.java"

                # Write file with UTF-8 encoding
                output_file = file_src_dir / java_filename
                output_file.write_text(file.code, encoding="utf-8")
                logger.info(f"Created {output_file} ({'test' if is_test_file else 'main'})")

            # Merge all dependencies
            pom_deps = []
            seen_coords = set()
            for dep in dependencies or []:
                if isinstance(dep, dict):
                    coord = (
                        dep.get("groupId"),
                        dep.get("artifactId"),
                        dep.get("version"),
                    )
                    if coord not in seen_coords:
                        pom_deps.append(dep)
                        seen_coords.add(coord)
                elif isinstance(dep, str):
                    parts = dep.split(":")
                    if len(parts) == 3:
                        coord = tuple(parts)
                        if coord not in seen_coords:
                            pom_deps.append(
                                {
                                    "groupId": parts[0],
                                    "artifactId": parts[1],
                                    "version": parts[2],
                                }
                            )
                            seen_coords.add(coord)

            # Auto-detect dependencies from file imports across all Java files
            for file in java_files:
                try:
                    detected = self._detect_java_dependencies(file.code)
                    for dd in detected:
                        coord = (dd.get("groupId"), dd.get("artifactId"), dd.get("version"))
                        if coord not in seen_coords:
                            pom_deps.append(dd)
                            seen_coords.add(coord)
                except Exception:
                    # Non-fatal: continue if detection fails for a file
                    continue

            # Check if this is a Spring Boot project and add essential starters
            has_spring = any(
                d.get("groupId", "").startswith("org.springframework") 
                for d in pom_deps
            )
            
            # Check if there are test files
            has_tests = any("Test" in f.filename for f in java_files)
            
            # Check if there are security-related files
            has_security = any(
                "security" in f.filename.lower() or "Security" in f.code
                for f in java_files
            )
            
            # Check if JWT is used
            has_jwt = any(
                "jwt" in f.filename.lower() or "Jwt" in f.code or "jsonwebtoken" in f.code.lower()
                for f in java_files
            )
            
            if has_spring:
                # Add essential Spring Boot starters if not already present
                essential_starters = [
                    ("org.springframework.boot", "spring-boot-starter-web", "3.1.5"),  # Always include web for REST APIs
                    ("org.springframework.boot", "spring-boot-starter-data-jpa", "3.1.5"),
                    ("org.springframework.boot", "spring-boot-starter-validation", "3.1.5"),
                ]
                
                # Add security if security files detected
                if has_security:
                    essential_starters.append(
                        ("org.springframework.boot", "spring-boot-starter-security", "3.1.5")
                    )
                
                # Add JWT dependencies if JWT is used
                if has_jwt:
                    essential_starters.extend([
                        ("io.jsonwebtoken", "jjwt-api", "0.11.5"),
                        ("io.jsonwebtoken", "jjwt-impl", "0.11.5"),
                        ("io.jsonwebtoken", "jjwt-jackson", "0.11.5"),
                    ])
                
                # Add test dependencies if test files exist
                if has_tests:
                    essential_starters.append(
                        ("org.springframework.boot", "spring-boot-starter-test", "3.1.5")
                    )
                
                for group, artifact, version in essential_starters:
                    coord = (group, artifact, version)
                    if coord not in seen_coords:
                        pom_deps.append({
                            "groupId": group,
                            "artifactId": artifact,
                            "version": version
                        })
                        seen_coords.add(coord)
                        logger.info(f"Added essential Spring Boot starter: {artifact}")

            # Create pom.xml
            if main_class:
                pom_content = self._generate_pom_xml(main_class, pom_deps)
            else:
                pom_content = self._generate_pom_xml("com.agenticcode.Main", pom_deps)

            (temp_dir / "pom.xml").write_text(pom_content, encoding="utf-8")
            logger.info("Created pom.xml")

            # Find Maven
            mvn_path = shutil.which("mvn")

            if not mvn_path and platform.system() == "Windows":
                common_paths = [
                    Path("C:/Program Files/apache-maven-3.9.11/bin/mvn.cmd"),
                    Path("C:/Program Files/apache-maven-3.9.10/bin/mvn.cmd"),
                    Path("C:/Program Files/apache-maven-3.9.9/bin/mvn.cmd"),
                    Path("C:/Program Files/apache-maven-3.8.8/bin/mvn.cmd"),
                ]
                for candidate in common_paths:
                    if candidate.exists():
                        mvn_path = str(candidate)
                        logger.info(f"Found Maven at: {mvn_path}")
                        break

            if not mvn_path:
                return BuildResult(
                    status="error",
                    errors=["Maven not found in system PATH"],
                    suggested_fixes=[
                        "Install Maven and add to PATH",
                        "Or use Maven wrapper (mvnw)",
                    ],
                )

            # Compile project
            if platform.system() == "Windows":
                run_cmd = f'"{mvn_path}" clean compile'
            else:
                run_cmd = f"{mvn_path} clean compile"

            compile_result = subprocess.run(
                run_cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
                shell=True,
            )

            if compile_result.returncode != 0:
                logger.error(f"Maven compilation failed")
                logger.error(f"Stdout: {compile_result.stdout}")
                logger.error(f"Stderr: {compile_result.stderr}")

                combined_output = compile_result.stderr + "\n" + compile_result.stdout
                parsed_errors = self._parse_java_errors(combined_output)
                errors.extend(parsed_errors["errors"])
                suggested_fixes.extend(parsed_errors["fixes"])
                
                # Extract Maven-specific error messages
                if "[ERROR]" in compile_result.stdout:
                    maven_errors = [line.strip() for line in compile_result.stdout.split('\n') if '[ERROR]' in line]
                    errors.extend(maven_errors[:10])  # Include up to 10 Maven error lines
                
                # If no errors extracted, include last part of output
                if not errors:
                    errors.append("Build failed - see logs for details")
                    errors.append(compile_result.stdout[-1000:] if compile_result.stdout else "No output")

                shutil.rmtree(temp_dir, ignore_errors=True)

                return BuildResult(
                    status="error",
                    errors=errors,
                    dependencies=[f"{d['groupId']}:{d['artifactId']}:{d['version']}" for d in pom_deps],
                    suggested_fixes=suggested_fixes,
                    build_instructions="Fix compilation errors",
                )

            logger.info("Java project compiled successfully")
            shutil.rmtree(temp_dir, ignore_errors=True)

            return BuildResult(
                status="success",
                dependencies=[f"{d['groupId']}:{d['artifactId']}:{d['version']}" for d in pom_deps],
                build_instructions="Project compiled successfully",
                suggested_fixes=[],
            )

        except Exception as e:
            logger.error(f"Java project build error: {str(e)}")
            return BuildResult(
                status="error",
                errors=[str(e)],
                suggested_fixes=["Review project structure and dependencies"],
            )
