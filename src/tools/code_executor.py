"""Safe code execution tools."""

import os
import sys

# import resource
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Tuple

from langchain.tools import tool

from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExecutionTimeout(Exception):
    """Raised when code execution times out."""

    pass


def timeout_handler(signum, frame):
    """Handler for execution timeout."""
    raise ExecutionTimeout("Code execution timed out")


@tool
def execute_python_code(code: str, runtime_credentials: Dict[str, str] = None) -> Dict[str, any]:
    """
    Execute Python code in a controlled environment.

    Args:
        code: Python code to execute
        runtime_credentials: Optional credentials to inject

    Returns:
        Execution result with stdout, stderr, and status
    """
    if not settings.enable_code_execution:
        return {"success": False, "error": "Code execution is disabled in settings"}

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            # Inject credentials if provided
            if runtime_credentials:
                logger.info(f"Injecting {len(runtime_credentials)} runtime credentials: {list(runtime_credentials.keys())}")
                credential_lines = "\n".join(
                    f"{key} = '{value}'" for key, value in runtime_credentials.items()
                )
                code = f"{credential_lines}\n\n{code}"
            else:
                logger.warning("No runtime credentials provided - code may fail if DB access needed")

            f.write(code)
            temp_file = f.name

        logger.info(f"Executing Python code from {temp_file}")

        # # Set resource limits if on Unix
        # def set_limits():
        #     if hasattr(resource, 'RLIMIT_AS'):
        #         # Limit memory
        #         max_memory = settings.max_memory_mb * 1024 * 1024
        #         resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))

        # Execute with timeout
        preexec_fn = set_limits if os.name != "nt" else None

        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=settings.execution_timeout,
            preexec_fn=preexec_fn,
        )

        # Clean up
        Path(temp_file).unlink(missing_ok=True)

        success = result.returncode == 0

        logger.info(f"Python execution {'succeeded' if success else 'failed'}")

        return {
            "success": success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        logger.error("Python execution timed out")
        Path(temp_file).unlink(missing_ok=True)
        return {
            "success": False,
            "error": f"Execution timed out after {settings.execution_timeout} seconds",
            "stdout": "",
            "stderr": "",
        }

    except Exception as e:
        logger.error(f"Python execution error: {str(e)}")
        return {"success": False, "error": str(e), "stdout": "", "stderr": ""}


@tool
def execute_java_code(
    code: str, classname: str, runtime_credentials: Dict[str, str] = None
) -> Dict[str, any]:
    """
    Compile and execute Java code using Maven for proper dependency management.

    Args:
        code: Java code to execute
        classname: Main class name
        runtime_credentials: Optional credentials to inject

    Returns:
        Execution result with stdout, stderr, and status
    """
    if not settings.enable_code_execution:
        return {"success": False, "error": "Code execution is disabled in settings"}

    try:
        import re

        # Create temporary Maven project
        temp_dir = Path(tempfile.mkdtemp())

        # Extract package name if present
        package_match = re.search(r"package\s+([\w.]+);", code)
        package_name = package_match.group(1) if package_match else None

        # Inject credentials if provided
        if runtime_credentials:
            credential_constants = "\n".join(
                f'    private static final String {key} = "{value}";'
                for key, value in runtime_credentials.items()
            )
            code = code.replace(
                f"public class {classname} {{",
                f"public class {classname} {{\n{credential_constants}\n",
            )

        # Create Maven project structure
        if package_name:
            package_path = package_name.replace(".", "/")
            src_dir = temp_dir / "src" / "main" / "java" / package_path
        else:
            src_dir = temp_dir / "src" / "main" / "java"

        src_dir.mkdir(parents=True, exist_ok=True)

        # Write Java file
        java_file = src_dir / f"{classname}.java"
        java_file.write_text(code, encoding="utf-8")

        # Create pom.xml
        main_class_path = f"{package_name}.{classname}" if package_name else classname
        pom_content = _generate_execution_pom(main_class_path)
        (temp_dir / "pom.xml").write_text(pom_content, encoding="utf-8")

        logger.info(f"Compiling Java code with Maven: {classname}")

        # Find Maven path (same as in build_agent.py)
        import shutil
        import platform
        
        mvn_path = shutil.which("mvn")
        if not mvn_path and platform.system() == "Windows":
            common_paths = [
                Path("C:/Program Files/apache-maven-3.9.11/bin/mvn.cmd"),
                Path("C:/Program Files/apache-maven-3.9.10/bin/mvn.cmd"),
                Path("C:/Program Files/apache-maven-3.9.9/bin/mvn.cmd"),
            ]
            for candidate in common_paths:
                if candidate.exists():
                    mvn_path = str(candidate)
                    break
        
        if not mvn_path:
            return {
                "success": False,
                "error": "Maven (mvn) not found in PATH or common installation locations",
                "stdout": "",
                "stderr": "",
            }
        
        # Compile with Maven
        compile_cmd = f'"{mvn_path}" clean compile -q' if platform.system() == "Windows" else "mvn clean compile -q"
        compile_result = subprocess.run(
            compile_cmd,
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
        )

        if compile_result.returncode != 0:
            logger.error(f"Maven compilation failed")
            logger.error(f"Compile stderr: {compile_result.stderr}")
            logger.error(f"Compile stdout: {compile_result.stdout}")
            return {
                "success": False,
                "compilation_error": compile_result.stderr,
                "stdout": compile_result.stdout,
                "stderr": compile_result.stderr,
            }

        logger.info("Java compilation succeeded, executing...")

        # Execute with Maven
        exec_cmd = f'"{mvn_path}" exec:java -Dexec.mainClass="{main_class_path}"'
        exec_result = subprocess.run(
            exec_cmd,
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=settings.execution_timeout,
            shell=True,
        )
        
        logger.info(f"Maven exec result: returncode={exec_result.returncode}")
        logger.info(f"Exec stdout: {exec_result.stdout}")
        logger.info(f"Exec stderr: {exec_result.stderr}")
        
        # Clean up
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

        success = exec_result.returncode == 0
        logger.info(f"Java execution {'succeeded' if success else 'failed'}")

        return {
            "success": success,
            "stdout": exec_result.stdout,
            "stderr": exec_result.stderr,
            "returncode": exec_result.returncode,
        }

    except subprocess.TimeoutExpired:
        logger.error("Java execution timed out")
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
        return {
            "success": False,
            "error": f"Execution timed out after {settings.execution_timeout} seconds",
            "stdout": "",
            "stderr": "",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "Maven (mvn) not found. Install Maven: sudo apt install maven (Linux) or brew install maven (macOS)",
            "stdout": "",
            "stderr": "",
        }
    except Exception as e:
        logger.error(f"Java execution error: {str(e)}")
        return {"success": False, "error": str(e), "stdout": "", "stderr": ""}


def _generate_execution_pom(main_class: str) -> str:
    """Generate minimal pom.xml for Java execution."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.agenticcode</groupId>
    <artifactId>execution</artifactId>
    <version>1.0</version>
    
    <properties>
        <maven.compiler.source>21</maven.compiler.source>
        <maven.compiler.target>21</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.apache.httpcomponents.client5</groupId>
            <artifactId>httpclient5</artifactId>
            <version>5.3</version>
        </dependency>
        <dependency>
            <groupId>com.google.code.gson</groupId>
            <artifactId>gson</artifactId>
            <version>2.10.1</version>
        </dependency>
        <dependency>
            <groupId>org.json</groupId>
            <artifactId>json</artifactId>
            <version>20231013</version>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.12.1</version>
            </plugin>
            <plugin>
                <groupId>org.codehaus.mojo</groupId>
                <artifactId>exec-maven-plugin</artifactId>
                <version>3.1.1</version>
                <configuration>
                    <mainClass>{main_class}</mainClass>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>"""


@tool
def install_python_dependencies(dependencies: list) -> Dict[str, any]:
    """
    Install Python dependencies using pip.

    Args:
        dependencies: List of package names

    Returns:
        Installation result
    """
    if not dependencies:
        return {"success": True, "message": "No dependencies to install"}

    try:
        logger.info(f"Installing dependencies: {dependencies}")

        # Sanitize dependency list: remove None, empty strings, obvious descriptions, and stdlib names
        sanitized = []
        removed = []
        
        # Project-internal module names that should never be installed
        project_internals = {"src", "app", "tests", "test", "config", "utils", "models", 
                            "schemas", "database", "api", "core", "services", "controllers", 
                            "views", "main", "lib", "common"}
        
        for d in dependencies:
            if not d:
                removed.append(d)
                continue
            s = str(d).strip()
            
            # Skip comment lines (starting with #)
            if s.startswith("#"):
                removed.append(f"{s} (comment)")
                continue
            
            # Filter out project-internal modules
            if s.lower() in project_internals:
                removed.append(f"{s} (project-internal)")
                continue
                
            # Skip obvious descriptions that contain parentheses or 'Standard'
            if ("(" in s and ")" in s) or "Standard" in s:
                removed.append(s)
                continue
            # Skip entries that are literal 'None' or start with 'none'
            if s.lower().startswith("none"):
                removed.append(s)
                continue
            sanitized.append(s)

        if removed:
            logger.warning(f"Removed invalid dependency entries before install: {removed}")
        
        logger.info(f"After initial sanitization: {sanitized}")

        if not sanitized:
            logger.info("No valid Python dependencies to install after sanitization")
            return {"success": True, "message": "No valid dependencies to install"}

        # Map common module names to pip package names when possible
        module_to_pip = {
            "bs4": "beautifulsoup4",
            "PIL": "Pillow",
            "Pillow": "Pillow",
            "sklearn": "scikit-learn",
            "cv2": "opencv-python",
            "yaml": "PyYAML",
            "lxml": "lxml",
            "np": "numpy",
            "pd": "pandas",
            "pandas": "pandas",
            "numpy": "numpy",
            "requests": "requests",
            "matplotlib": "matplotlib",
            "bs": "beautifulsoup4",
            "scipy": "scipy",
            "sympy": "sympy",
            "seaborn": "seaborn",
            "scikit": "scikit-learn",
        }

        pip_packages = []
        for s in sanitized:
            # leave version specifiers intact
            if any(op in s for op in ("==", ">=", "<=", "~=")):
                pip_packages.append(s)
                continue
            # if dotted module, pick first segment
            top = s.split(".")[0]
            mapped = module_to_pip.get(top, top)
            pip_packages.append(mapped)

        # Remove duplicates while preserving order
        seen = set()
        final_packages = []
        for p in pip_packages:
            # Skip Python standard library modules that shouldn't be installed
            stdlib_ignore = {
                "logging", "typing", "json", "math", "itertools", "collections", "datetime", "re", "sys", "os",
                "unittest", "pathlib", "io", "subprocess", "tempfile", "shutil", "copy", "pickle",
                "threading", "multiprocessing", "argparse", "configparser", "email", "urllib", "http",
                "socket", "ssl", "asyncio", "hashlib", "hmac", "secrets", "uuid", "enum", "dataclasses",
                "abc", "time", "csv", "functools", "random", "string", "textwrap", "difflib", "warnings",
                "sqlite3", "dbm", "shelve"
            }
            # Skip project-internal modules
            project_modules = {"src", "app", "tests", "test", "config", "utils", "models", "schemas", "database", "api", "core", "services", "controllers", "views", "main"}
            
            if p in stdlib_ignore or p in project_modules:
                continue
            if p not in seen:
                final_packages.append(p)
                seen.add(p)

        logger.info(f"Final pip packages to install: {final_packages}")

        # Change to a safe directory to avoid pip trying to install from cwd
        # if there's a setup.py or pyproject.toml present
        import os
        import tempfile
        original_cwd = os.getcwd()
        safe_dir = tempfile.gettempdir()
        
        try:
            os.chdir(safe_dir)
            logger.info(f"Changed to safe directory for pip install: {safe_dir}")
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + final_packages,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes for installations
            )
        finally:
            os.chdir(original_cwd)
            logger.info(f"Restored original directory: {original_cwd}")

        success = result.returncode == 0

        # If pip module is missing in this Python installation, attempt to bootstrap it
        if not success and "No module named pip" in (result.stderr or ""):
            logger.warning("pip module missing; attempting to bootstrap pip via ensurepip")
            try:
                ensure = subprocess.run(
                    [sys.executable, "-m", "ensurepip", "--upgrade"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                logger.info(f"ensurepip stdout: {ensure.stdout}")
                logger.info(f"ensurepip stderr: {ensure.stderr}")
            except Exception as e:
                logger.error(f"ensurepip failed: {e}")

            # Retry pip install once
            try:
                os.chdir(safe_dir)
                retry = subprocess.run(
                    [sys.executable, "-m", "pip", "install"] + final_packages,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            finally:
                os.chdir(original_cwd)
                
            success = retry.returncode == 0
            if success:
                logger.info("Dependencies installed successfully after ensurepip")
                return {"success": True, "stdout": retry.stdout, "stderr": retry.stderr}
            else:
                logger.error(f"Dependency installation still failed after ensurepip: {retry.stderr}")
                return {"success": False, "stdout": retry.stdout, "stderr": retry.stderr}

        if success:
            logger.info("Dependencies installed successfully")
        else:
            logger.error(f"Dependency installation failed: {result.stderr}")

        return {"success": success, "stdout": result.stdout, "stderr": result.stderr}

    except Exception as e:
        logger.error(f"Error installing dependencies: {str(e)}")
        return {"success": False, "error": str(e)}
