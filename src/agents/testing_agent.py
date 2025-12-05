"""Testing and validation agent."""

import json
import time
from typing import Dict

from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.prompts import TESTING_AGENT_HUMAN_TEMPLATE, TESTING_AGENT_SYSTEM_PROMPT
from src.config.settings import settings
from src.models.schemas import PerformanceMetrics, ProgrammingLanguage, TestCase, TestResult
from src.tools.code_executor import execute_java_code, execute_python_code
from src.utils.logger import test_logger as logger


class TestingAgent:
    """Agent responsible for testing and validating generated code."""

    def __init__(self):
        """Initialize the testing agent."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
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
