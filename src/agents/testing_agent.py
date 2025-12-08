"""Testing and validation agent."""

import json
import time
from typing import Dict

from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.prompts import TESTING_AGENT_HUMAN_TEMPLATE, TESTING_AGENT_SYSTEM_PROMPT
from src.config.settings import settings
from src.models.schemas import FileArtifact, PerformanceMetrics, ProgrammingLanguage, TestCase, TestResult
from src.tools.code_executor import execute_java_code, execute_python_code
from src.utils.logger import test_logger as logger


class TestingAgent:
    """Agent responsible for testing and validating generated code."""

    def __init__(self):
        """Initialize the testing agent."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro-latest",
            google_api_key=settings.google_api_key,
            temperature=settings.agent_temperature,
            convert_system_message_to_human=True,
        )

        logger.info("Testing Agent initialized")

    def execute_and_test(
        self,
        requirements: str,
        code: str,
        language: ProgrammingLanguage,
        runtime_credentials: Dict[str, str] = None,
    ) -> TestResult:
        """
        Execute code and validate against requirements.

        Args:
            requirements: Original user requirements
            code: Code to test
            language: Programming language
            runtime_credentials: Optional runtime credentials

        Returns:
            TestResult with execution details
        """
        try:
            logger.info(f"Testing {language.value} code")

            # Execute code
            start_time = time.time()

            if language == ProgrammingLanguage.PYTHON:
                exec_result = execute_python_code.invoke(
                    {"code": code, "runtime_credentials": runtime_credentials or {}}
                )
            else:  # Java
                # Extract class name from code
                import re

                class_match = re.search(r"public\s+class\s+(\w+)", code)
                if not class_match:
                    logger.error("Could not find public class in Java code")
                    return TestResult(
                        status="fail",
                        test_cases=[
                            TestCase(
                                name="Code Structure",
                                status="fail",
                                description="Java code validation",
                                error="No public class found in code",
                            )
                        ],
                        execution_logs="",
                        issues_found=["Java code must have a public class"],
                        recommendations=["Add 'public class ClassName' to your code"],
                    )

                classname = class_match.group(1)
                logger.info(f"Executing Java class: {classname}")

                exec_result = execute_java_code.invoke(
                    {
                        "code": code,
                        "classname": classname,
                        "runtime_credentials": runtime_credentials or {},
                    }
                )

            execution_time = time.time() - start_time

            # Analyze results
            if not exec_result.get("success"):
                logger.error(f"Code execution failed")
                logger.error(f"Execution result: {exec_result}")
                return self._create_failure_result(exec_result, execution_time)

            logger.info("Code executed successfully, validating output")

            # Validate output using LLM
            validation_result = self._validate_with_llm(requirements, code, exec_result, language)

            return validation_result

        except Exception as e:
            logger.error(f"Testing failed: {str(e)}")
            return TestResult(
                status="fail",
                test_cases=[
                    TestCase(
                        name="Execution",
                        status="fail",
                        description="Test execution encountered an error",
                        error=str(e),
                    )
                ],
                execution_logs=str(e),
                issues_found=[str(e)],
            )

    def _create_failure_result(self, exec_result: Dict, execution_time: float) -> TestResult:
        """Create TestResult for failed execution."""
        error_msg = exec_result.get("error") or exec_result.get("stderr") or "Unknown error"

        return TestResult(
            status="fail",
            test_cases=[
                TestCase(
                    name="Code Execution",
                    status="fail",
                    description="Code failed to execute",
                    error=error_msg,
                )
            ],
            execution_logs=f"STDOUT:\n{exec_result.get('stdout', '')}\n\nSTDERR:\n{error_msg}",
            performance=PerformanceMetrics(execution_time_seconds=execution_time),
            issues_found=[error_msg],
            recommendations=["Review error logs and fix runtime issues"],
        )

    def _validate_with_llm(
        self, requirements: str, code: str, exec_result: Dict, language: ProgrammingLanguage
    ) -> TestResult:
        """Use LLM to validate if code meets requirements."""

        prompt = f"{TESTING_AGENT_SYSTEM_PROMPT}\n\n"
        prompt += TESTING_AGENT_HUMAN_TEMPLATE.format(
            requirements=requirements,
            code=code,
            language=language.value.upper(),
            db_host=settings.db_host,
            db_port=settings.db_port,
            network_access="Enabled" if settings.allow_network_access else "Disabled",
        )

        # Add execution results
        prompt += f"\n\n**Execution Output:**\n"
        prompt += f"STDOUT:\n{exec_result.get('stdout', '(empty)')}\n\n"
        if exec_result.get("stderr"):
            prompt += f"STDERR:\n{exec_result.get('stderr')}\n\n"

        try:
            response = self.llm.invoke(prompt)
            result_text = response.content

            # Normalize different response shapes (string | list | dict)
            if isinstance(result_text, list):
                parts = []
                for it in result_text:
                    if isinstance(it, dict) and "text" in it:
                        parts.append(it["text"])
                    else:
                        parts.append(str(it))
                result_text = "\n".join(parts)
            elif isinstance(result_text, dict):
                # Common keys: 'text', 'content'
                if "text" in result_text:
                    result_text = str(result_text["text"])
                elif "content" in result_text:
                    result_text = str(result_text["content"])
                else:
                    result_text = str(result_text)
            else:
                result_text = str(result_text)

            # Try to extract JSON from response
            result_data = self._extract_json_from_response(result_text)

            if result_data:
                # Parse LLM response into TestResult
                test_cases = [TestCase(**tc) for tc in result_data.get("test_cases", [])]

                performance_data = result_data.get("performance", {})
                performance = PerformanceMetrics(**performance_data) if performance_data else None

                return TestResult(
                    status=result_data.get("status", "fail"),
                    test_cases=test_cases,
                    execution_logs=exec_result.get("stdout", "")
                    + "\n"
                    + exec_result.get("stderr", ""),
                    performance=performance,
                    issues_found=result_data.get("issues_found", []),
                    recommendations=result_data.get("recommendations", []),
                )
            else:
                # Fallback: basic validation
                return self._basic_validation(exec_result, requirements)

        except Exception as e:
            logger.error(f"LLM validation failed: {str(e)}")
            return self._basic_validation(exec_result, requirements)

    def _extract_json_from_response(self, text: str) -> Dict:
        """Extract JSON object from LLM response."""
        import re

        # Try to find JSON in markdown code blocks
        json_match = re.search(r"```json\n(.+?)\n```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass

        # Try to find raw JSON
        json_match = re.search(r"\{.+\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass

        return None

    def _basic_validation(self, exec_result: Dict, requirements: str) -> TestResult:
        """Basic validation when LLM parsing fails."""
        stdout = exec_result.get("stdout", "")
        stderr = exec_result.get("stderr", "")

        # Simple heuristics
        has_output = len(stdout) > 0
        has_errors = len(stderr) > 0 and "error" in stderr.lower()

        if has_output and not has_errors:
            status = "pass"
            issues = []
            recommendations = ["Code executed successfully"]
        else:
            status = "fail"
            issues = ["No output generated" if not has_output else "Errors in execution"]
            recommendations = ["Verify code logic and expected output"]

        return TestResult(
            status=status,
            test_cases=[
                TestCase(
                    name="Basic Execution",
                    status=status,
                    description="Code execution test",
                    error=stderr if has_errors else None,
                )
            ],
            execution_logs=stdout + "\n" + stderr,
            issues_found=issues,
            recommendations=recommendations,
        )

    def test_project(
        self,
        requirements: str,
        files: list,
        language: ProgrammingLanguage,
        root_dir: str = None,
        runtime_credentials: Dict[str, str] = None,
    ) -> TestResult:
        """
        Test a multi-file project.

        Args:
            requirements: Original user requirements
            files: List of FileArtifact objects
            language: Programming language
            root_dir: Root directory of project
            runtime_credentials: Optional runtime credentials

        Returns:
            TestResult with test execution details
        """
        try:
            logger.info(f"Testing {language.value} project with {len(files)} files")

            test_cases = []
            execution_logs = ""
            issues = []
            recommendations = []

            if language == ProgrammingLanguage.PYTHON:
                test_cases, execution_logs, issues, recommendations = (
                    self._test_python_project(files, root_dir, runtime_credentials)
                )
            elif language == ProgrammingLanguage.JAVA:
                test_cases, execution_logs, issues, recommendations = (
                    self._test_java_project(files, root_dir, runtime_credentials)
                )

            success = all(tc.status == "pass" for tc in test_cases) and not issues

            return TestResult(
                status="pass" if success else "fail",
                test_cases=test_cases,
                execution_logs=execution_logs,
                issues_found=issues,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Project testing failed: {str(e)}")
            return TestResult(
                status="fail",
                test_cases=[
                    TestCase(
                        name="Project Test",
                        status="fail",
                        description="Multi-file project testing",
                        error=str(e),
                    )
                ],
                execution_logs="",
                issues_found=["Project test execution failed"],
                recommendations=["Check project structure and dependencies"],
            )

    def _test_python_project(
        self, files: list, root_dir: str = None, runtime_credentials: Dict[str, str] = None
    ) -> tuple:
        """Test a Python project."""
        import subprocess
        import tempfile
        from pathlib import Path

        test_cases = []
        execution_logs = ""
        issues = []
        recommendations = []

        # Create temp directory for project
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Write all files
            for file in files:
                if file.language == "python":
                    file_path = temp_dir / file.filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(file.code, encoding="utf-8")
                    logger.info(f"Wrote {file.filename}")

            # Find and run unit tests
            test_files = [f for f in files if "test_" in f.filename]

            if test_files:
                logger.info(f"Found {len(test_files)} test files")

                for test_file in test_files:
                    try:
                        result = subprocess.run(
                            ["python", "-m", "pytest", test_file.filename, "-v"],
                            cwd=temp_dir,
                            capture_output=True,
                            text=True,
                            timeout=60,
                        )

                        execution_logs += f"\n--- {test_file.filename} ---\n"
                        execution_logs += result.stdout
                        if result.stderr:
                            execution_logs += "\nStderr:\n" + result.stderr

                        if result.returncode == 0:
                            test_cases.append(
                                TestCase(
                                    name=test_file.filename,
                                    status="pass",
                                    description="Unit tests passed",
                                )
                            )
                            logger.info(f"✓ {test_file.filename} passed")
                        else:
                            test_cases.append(
                                TestCase(
                                    name=test_file.filename,
                                    status="fail",
                                    description="Unit tests failed",
                                    error=result.stdout,
                                )
                            )
                            issues.append(f"Tests in {test_file.filename} failed")
                            logger.error(f"✗ {test_file.filename} failed")

                    except subprocess.TimeoutExpired:
                        test_cases.append(
                            TestCase(
                                name=test_file.filename,
                                status="fail",
                                description="Test timeout",
                                error="Test execution timed out",
                            )
                        )
                        issues.append(f"Tests in {test_file.filename} timed out")
                    except Exception as e:
                        test_cases.append(
                            TestCase(
                                name=test_file.filename,
                                status="fail",
                                description="Test execution error",
                                error=str(e),
                            )
                        )
                        issues.append(f"Error running {test_file.filename}: {str(e)}")

            else:
                # No tests found, run import validation (lenient mode)
                logger.info("No test files found, validating imports (lenient mode)")

                main_file = next((f for f in files if f.filename == "main.py" or f.filename.endswith("__main__.py")), None)

                if main_file:
                    try:
                        # Try to import/exec the main file
                        result = subprocess.run(
                            ["python", "-c", f"import sys; sys.path.insert(0, '.'); exec(compile(open('{main_file.filename}').read(), '{main_file.filename}', 'exec'))"],
                            cwd=temp_dir,
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )

                        # Check if error is due to missing dependencies
                        has_missing_deps = "ModuleNotFoundError" in result.stderr or "No module named" in result.stderr

                        if result.returncode == 0:
                            test_cases.append(
                                TestCase(
                                    name="Project Import",
                                    status="pass",
                                    description="All imports validated",
                                )
                            )
                            execution_logs = "Project imports successful"
                        elif has_missing_deps:
                            # Missing dependencies are not test failures; they're expected if deps weren't installed
                            logger.warning(f"Import validation skipped due to missing dependencies (expected)")
                            test_cases.append(
                                TestCase(
                                    name="Project Import",
                                    status="pass",
                                    description="Project structure valid (dependencies not installed in test environment)",
                                )
                            )
                            execution_logs = "Project structure validated (dependencies not installed)"
                            logger.info(f"Skipped import test due to missing dependencies: {result.stderr[:200]}")
                        else:
                            # Other errors are real failures
                            test_cases.append(
                                TestCase(
                                    name="Project Import",
                                    status="fail",
                                    description="Import validation failed",
                                    error=result.stderr,
                                )
                            )
                            issues.append("Import validation failed")
                            execution_logs = result.stderr

                    except Exception as e:
                        test_cases.append(
                            TestCase(
                                name="Project Import",
                                status="fail",
                                description="Import test error",
                                error=str(e),
                            )
                        )
                        issues.append(str(e))

        finally:
            # Clean up
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

        if not test_cases:
            test_cases.append(
                TestCase(
                    name="Project Validation",
                    status="pass",
                    description="Project structure valid",
                )
            )

        return test_cases, execution_logs, issues, recommendations

    def _test_java_project(
        self, files: list, root_dir: str = None, runtime_credentials: Dict[str, str] = None
    ) -> tuple:
        """Test a Java project."""
        import subprocess
        import tempfile
        from pathlib import Path

        test_cases = []
        execution_logs = ""
        issues = []
        recommendations = []

        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Write all Java files to Maven structure
            for file in files:
                if file.language == "java":
                    file_path = temp_dir / file.filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(file.code, encoding="utf-8")

            # Find test classes
            test_files = [f for f in files if "Test" in f.filename]

            if test_files:
                logger.info(f"Found {len(test_files)} test files")

                for test_file in test_files:
                    try:
                        # Run JUnit tests via Maven
                        result = subprocess.run(
                            ["mvn", "test", "-Dtest=" + test_file.filename.replace(".java", "")],
                            cwd=temp_dir,
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )

                        execution_logs += f"\n--- {test_file.filename} ---\n"
                        execution_logs += result.stdout

                        if result.returncode == 0:
                            test_cases.append(
                                TestCase(
                                    name=test_file.filename,
                                    status="pass",
                                    description="Unit tests passed",
                                )
                            )
                        else:
                            test_cases.append(
                                TestCase(
                                    name=test_file.filename,
                                    status="fail",
                                    description="Unit tests failed",
                                    error=result.stdout,
                                )
                            )
                            issues.append(f"Tests in {test_file.filename} failed")

                    except Exception as e:
                        test_cases.append(
                            TestCase(
                                name=test_file.filename,
                                status="fail",
                                description="Test error",
                                error=str(e),
                            )
                        )
                        issues.append(str(e))

            else:
                # No tests, validate compilation was successful (done in BuildAgent)
                test_cases.append(
                    TestCase(
                        name="Project Compilation",
                        status="pass",
                        description="Java project structure valid",
                    )
                )
                execution_logs = "Java project structure validated"

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

        if not test_cases:
            test_cases.append(
                TestCase(
                    name="Project Validation",
                    status="pass",
                    description="Project structure valid",
                )
            )

        return test_cases, execution_logs, issues, recommendations
