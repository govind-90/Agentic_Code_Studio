"""Intelligent error parsing and context extraction."""

import re
from typing import Dict, List, Optional, Tuple

from src.models.schemas import ErrorType


class ErrorParser:
    """Parse and structure error messages for agent feedback."""

    # Common error patterns
    PYTHON_SYNTAX_ERROR = re.compile(r"SyntaxError: (.+?) \(line (\d+)\)")
    PYTHON_IMPORT_ERROR = re.compile(r"ModuleNotFoundError: No module named '(.+?)'")
    PYTHON_NAME_ERROR = re.compile(r"NameError: name '(.+?)' is not defined")
    PYTHON_TYPE_ERROR = re.compile(r"TypeError: (.+)")

    JAVA_COMPILE_ERROR = re.compile(r"(\w+\.java):(\d+): error: (.+)")
    JAVA_CLASS_NOT_FOUND = re.compile(r"class, interface, or enum expected")
    JAVA_SYMBOL_ERROR = re.compile(r"cannot find symbol\s+symbol:\s+(\w+)\s+(\w+)")
    JAVA_PACKAGE_ERROR = re.compile(r"package (.+?) does not exist")
    JAVA_INCOMPATIBLE_TYPES = re.compile(r"incompatible types: (.+?) cannot be converted to (.+)")
    JAVA_METHOD_ERROR = re.compile(r"cannot find symbol\s+symbol:\s+method (.+?)\(")

    DB_CONNECTION_ERROR = re.compile(r"could not connect|connection refused|access denied", re.I)
    API_ERROR = re.compile(r"HTTP Error (\d+)|ConnectionError|Timeout", re.I)

    MISSING_API_KEY = re.compile(r"api[_\s]?key|authorization|authentication", re.I)

    @staticmethod
    def parse_error(
        error_message: str, language: str, code: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Parse error message and extract structured information.

        Args:
            error_message: Raw error message/stack trace
            language: Programming language (python/java)
            code: Original code for context

        Returns:
            Structured error information
        """
        # Defensive coercion: ensure we operate on strings to avoid TypeErrors
        if error_message is None:
            error_message = ""
        else:
            error_message = str(error_message)

        if code is not None:
            code = str(code)

        error_type = ErrorParser._determine_error_type(error_message, language)
        root_cause = ErrorParser._extract_root_cause(error_message, error_type, language)
        issues = ErrorParser._extract_specific_issues(error_message, language)
        fixes = ErrorParser._suggest_fixes(error_type, issues, language)
        missing_creds = ErrorParser._detect_missing_credentials(error_message, code)

        return {
            "error_type": error_type,
            "root_cause": root_cause,
            "specific_issues": issues,
            "suggested_fixes": fixes,
            "missing_credentials": missing_creds,
            "raw_error": error_message,
        }

    @staticmethod
    def _determine_error_type(error_message: str, language: str) -> ErrorType:
        """Determine the type of error."""
        error_lower = error_message.lower()

        if ErrorParser.MISSING_API_KEY.search(error_message):
            return ErrorType.MISSING_CREDENTIALS

        if language == "python":
            if "syntaxerror" in error_lower or "indentationerror" in error_lower:
                return ErrorType.SYNTAX
            if "modulenotfounderror" in error_lower or "importerror" in error_lower:
                return ErrorType.BUILD
            if ErrorParser.DB_CONNECTION_ERROR.search(error_message):
                return ErrorType.RUNTIME
            if ErrorParser.API_ERROR.search(error_message):
                return ErrorType.RUNTIME
            if any(err in error_lower for err in ["nameerror", "typeerror", "valueerror"]):
                return ErrorType.RUNTIME

        elif language == "java":
            if "error:" in error_lower and ".java:" in error_lower:
                return ErrorType.SYNTAX
            if "class not found" in error_lower or "classnotfoundexception" in error_lower:
                return ErrorType.RUNTIME
            if "package does not exist" in error_lower:
                return ErrorType.BUILD
            if "cannot find symbol" in error_lower:
                return ErrorType.SYNTAX
            if "nosuchmethoderror" in error_lower or "nosuchfielderror" in error_lower:
                return ErrorType.RUNTIME

        # Default to logic error if can't determine
        return ErrorType.LOGIC

    @staticmethod
    def _extract_root_cause(error_message: str, error_type: ErrorType, language: str) -> str:
        """Extract the root cause description."""
        if error_type == ErrorType.MISSING_CREDENTIALS:
            return "Required API keys or credentials are missing"

        # Python specific
        if language == "python":
            if match := ErrorParser.PYTHON_IMPORT_ERROR.search(error_message):
                return f"Missing Python package: {match.group(1)}"
            if match := ErrorParser.PYTHON_SYNTAX_ERROR.search(error_message):
                return f"Syntax error on line {match.group(2)}: {match.group(1)}"
            if match := ErrorParser.PYTHON_NAME_ERROR.search(error_message):
                return f"Undefined variable or function: {match.group(1)}"

        # Java specific
        elif language == "java":
            if match := ErrorParser.JAVA_COMPILE_ERROR.search(error_message):
                return (
                    f"Compilation error in {match.group(1)} line {match.group(2)}: {match.group(3)}"
                )
            if match := ErrorParser.JAVA_PACKAGE_ERROR.search(error_message):
                return f"Missing dependency: package {match.group(1)} not found"
            if match := ErrorParser.JAVA_SYMBOL_ERROR.search(error_message):
                return f"Undefined {match.group(1)}: {match.group(2)}"
            if "ClassNotFoundException" in error_message:
                class_match = re.search(r"ClassNotFoundException: (.+)", error_message)
                class_name = class_match.group(1) if class_match else "unknown"
                return f"Class not found at runtime: {class_name}"
            if "NoSuchMethodError" in error_message:
                return (
                    "Method signature mismatch - wrong method called or dependency version conflict"
                )

        # Generic extraction - first line of error
        lines = error_message.strip().split("\n")
        return lines[0][:200] if lines else "Unknown error"

    @staticmethod
    def _extract_specific_issues(error_message: str, language: str) -> List[str]:
        """Extract specific issues from error message."""
        issues = []

        # Extract missing imports
        for match in ErrorParser.PYTHON_IMPORT_ERROR.finditer(error_message):
            issues.append(f"Missing package: {match.group(1)}")

        # Extract syntax errors with line numbers
        for match in ErrorParser.PYTHON_SYNTAX_ERROR.finditer(error_message):
            issues.append(f"Line {match.group(2)}: {match.group(1)}")

        # Extract Java compilation errors
        for match in ErrorParser.JAVA_COMPILE_ERROR.finditer(error_message):
            issues.append(f"{match.group(1)}:{match.group(2)} - {match.group(3)}")

        # Java symbol errors
        if ErrorParser.JAVA_SYMBOL_ERROR.search(error_message):
            issues.append("Cannot find symbol - missing import or undefined variable/method")

        # Java package errors
        for match in ErrorParser.JAVA_PACKAGE_ERROR.finditer(error_message):
            issues.append(f"Package not found: {match.group(1)} - add Maven dependency")

        # Java type errors
        for match in ErrorParser.JAVA_INCOMPATIBLE_TYPES.finditer(error_message):
            issues.append(f"Type mismatch: {match.group(1)} cannot convert to {match.group(2)}")

        # Java method errors
        for match in ErrorParser.JAVA_METHOD_ERROR.finditer(error_message):
            issues.append(f"Method not found: {match.group(1)}")

        # Runtime errors
        if "ClassNotFoundException" in error_message:
            issues.append("Class not found at runtime - check classpath or Maven dependencies")

        if "NoSuchMethodError" in error_message:
            issues.append(
                "Method not found at runtime - dependency version conflict or wrong method signature"
            )

        # Database connection issues
        if ErrorParser.DB_CONNECTION_ERROR.search(error_message):
            issues.append(
                "Database connection failed - verify PostgreSQL is running and credentials are correct"
            )

        # API call issues
        if ErrorParser.API_ERROR.search(error_message):
            issues.append("External API call failed - check network connectivity and API endpoint")

        return issues if issues else ["See raw error for details"]

    @staticmethod
    def _suggest_fixes(error_type: ErrorType, issues: List[str], language: str) -> List[str]:
        """Suggest actionable fixes based on error type."""
        fixes = []

        if error_type == ErrorType.SYNTAX:
            fixes.append("Review code syntax and fix any typos or structural errors")
            fixes.append("Ensure proper indentation (Python) or bracket matching (Java)")

        elif error_type == ErrorType.BUILD:
            if language == "python":
                fixes.append("Add missing packages to requirements.txt")
                fixes.append("Ensure all imports are available and correctly spelled")
            else:  # Java
                fixes.append("Add missing Maven dependencies to pom.xml")
                fixes.append("Verify package names and imports")
                fixes.append("Check Maven repository connectivity")
                fixes.append("Use correct groupId:artifactId:version format")

        elif error_type == ErrorType.RUNTIME:
            fixes.append("Add proper error handling (try-except or try-catch)")
            fixes.append("Validate inputs and handle edge cases")
            fixes.append("Check external service availability (database, APIs)")

        elif error_type == ErrorType.MISSING_CREDENTIALS:
            fixes.append("Prompt user to provide required credentials")
            fixes.append("Add credential parameters to function signatures")

        else:  # LOGIC
            fixes.append("Review algorithm logic and data flow")
            fixes.append("Add debug logging to trace execution")
            fixes.append("Verify expected vs actual behavior")

        return fixes

    @staticmethod
    def _detect_missing_credentials(error_message: str, code: Optional[str]) -> List[str]:
        """Detect if API keys or credentials are missing."""
        missing = []

        # Check error message for auth-related keywords
        if ErrorParser.MISSING_API_KEY.search(error_message):
            missing.append("API Key or Authentication Token")

        # Check code for common API patterns
        if code:
            # Check for API key placeholders
            if re.search(r"api[_]?key\s*=\s*['\"]YOUR_|TODO|REPLACE", code, re.I):
                missing.append("API Key (found placeholder in code)")

            # Check for common API endpoints
            if re.search(r"api\.openweathermap\.org|api\.time\.io", code, re.I):
                if "api_key" not in code.lower() and "apikey" not in code.lower():
                    missing.append("API Key for external service")

        return missing

    @staticmethod
    def format_error_context(
        parsed_error: Dict[str, any], iteration: int, max_iterations: int
    ) -> str:
        """Format parsed error into agent-readable context."""
        from src.config.prompts import ERROR_CONTEXT_TEMPLATE

        return ERROR_CONTEXT_TEMPLATE.format(
            error_type=parsed_error["error_type"].value.upper(),
            root_cause=parsed_error["root_cause"],
            issues="\n".join(f"- {issue}" for issue in parsed_error["specific_issues"]),
            fixes="\n".join(f"- {fix}" for fix in parsed_error["suggested_fixes"]),
            iteration=iteration,
            max_iterations=max_iterations,
        )
