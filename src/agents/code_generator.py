"""Code generation agent using LangChain."""

from typing import Dict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.prompts import CODE_GENERATOR_HUMAN_TEMPLATE, CODE_GENERATOR_SYSTEM_PROMPT
from src.config.settings import settings
from src.models.schemas import ProgrammingLanguage
from src.utils.logger import code_gen_logger as logger


class CodeGeneratorAgent:
    """Agent responsible for generating code from requirements."""

    def __init__(self):
        """Initialize the code generator agent."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=settings.google_api_key,
            temperature=settings.agent_temperature,
            convert_system_message_to_human=True,
        )

        logger.info("Code Generator Agent initialized")

    def generate_code(
        self, requirements: str, language: ProgrammingLanguage, error_context: str = ""
    ) -> Dict[str, any]:
        """
        Generate code based on requirements.

        Args:
            requirements: User's natural language requirements
            language: Target programming language
            error_context: Optional context from previous failed attempts

        Returns:
            Generated code and metadata
        """
        try:
            logger.info(f"Generating {language.value} code for requirements")

            # Build prompt
            prompt_text = f"{CODE_GENERATOR_SYSTEM_PROMPT}\n\n"
            prompt_text += CODE_GENERATOR_HUMAN_TEMPLATE.format(
                requirements=requirements,
                language=language.value.upper(),
                error_context=error_context if error_context else "",
            )

            # Generate code using LLM
            response = self.llm.invoke(prompt_text)
            generated_code = response.content

            # Handle different response formats from LLM
            # response.content could be:
            # 1. A string: "code here"
            # 2. A list of dicts: [{'type': 'text', 'text': 'code here'}, ...]
            # 3. A list of strings: ['code here', ...]
            if isinstance(generated_code, list):
                # Extract text from list of dicts or strings
                text_parts = []
                for item in generated_code:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    else:
                        text_parts.append(str(item))
                generated_code = "\n".join(text_parts)
            else:
                generated_code = str(generated_code) if generated_code else ""

            # Extract code from markdown blocks if present
            generated_code = self._extract_code_from_markdown(generated_code, language)

            # Extract dependencies
            dependencies = self._extract_dependencies(generated_code, language)

            # Attempt to split the generated text into multiple file artifacts
            import re

            files = []

            # First, detect explicit file markers like '# FILE: path/to/file' or '// FILE: path/to/file'
            file_marker_pattern = re.compile(r"(?m)^(?:#|//)\s*FILE:\s*(.+)$")
            markers = list(file_marker_pattern.finditer(generated_code))

            if markers:
                for i, m in enumerate(markers):
                    filename = m.group(1).strip()
                    start = m.end()
                    end = markers[i + 1].start() if i + 1 < len(markers) else len(generated_code)
                    content = generated_code[start:end].strip()
                    # Normalize leading/trailing code fences inside content
                    if content.startswith("```") and content.endswith("```"):
                        content = re.sub(r"^```[\w]*\n", "", content)
                        content = re.sub(r"\n```$", "", content)
                    files.append({"filename": filename, "code": content})

            elif code_blocks := re.findall(r"```(?:\\w+)?\\n(.+?)```", generated_code, re.DOTALL):
                # 1) Find fenced code blocks and treat each as a file
                for idx, block in enumerate(code_blocks):
                    # Try to infer filename from a leading comment like '# filename: src/main.py' or '// filename: src/Main.java'
                    filename = None
                    first_lines = "\n".join(block.splitlines()[:5])
                    m = re.search(r"(?:#|//)\s*(?:filename|file|path)[:=]\s*(.+)", first_lines, re.IGNORECASE)
                    if m:
                        filename = m.group(1).strip()

                    # If Java, try to infer from public class name
                    if not filename and language == ProgrammingLanguage.JAVA:
                        cm = re.search(r"public\s+class\s+(\w+)", block)
                        if cm:
                            filename = f"{cm.group(1)}.java"

                    # Default filename
                    ext = "py" if language == ProgrammingLanguage.PYTHON else "java"
                    if not filename:
                        filename = f"generated_{idx + 1}.{ext}"

                    files.append({"filename": filename, "code": block.strip()})

            else:
                # 2) No fenced blocks: if the whole text looks like one file, return it
                if generated_code.strip():
                    files.append({
                        "filename": self._generate_filename(language, generated_code),
                        "code": generated_code.strip(),
                    })

            logger.info(f"Code generation completed. Dependencies: {dependencies}")

            return {
                "success": True,
                "files": files,
                "language": language.value,
                "dependencies": dependencies,
            }

        except Exception as e:
            logger.error(f"Code generation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _extract_code_from_markdown(self, text: str, language: ProgrammingLanguage) -> str:
        """Extract code from markdown code blocks."""
        import re

        # Defensive: ensure text is a string
        if not isinstance(text, str):
            text = str(text) if text else ""

        # Try to find code block with language specifier
        pattern = f"```{language.value}\\n(.+?)```"
        match = re.search(pattern, text, re.DOTALL)

        if match:
            return match.group(1).strip()

        # Try to find any code block
        pattern = "```\\n(.+?)```"
        match = re.search(pattern, text, re.DOTALL)

        if match:
            return match.group(1).strip()

        # Return as-is if no code blocks found
        return text.strip()

    def _extract_dependencies(self, code: str, language: ProgrammingLanguage) -> list:
        """Extract dependencies from code."""
        dependencies = []

        if language == ProgrammingLanguage.PYTHON:
            # Extract from imports
            import re

            # Standard imports (import X)
            imports = re.findall(r"^import\s+(\w+)", code, re.MULTILINE)
            dependencies.extend(imports)

            # From imports (from X import Y)
            from_imports = re.findall(r"^from\s+(\w+)", code, re.MULTILINE)
            dependencies.extend(from_imports)

            # Look for REQUIRES comment
            requires_match = re.search(r"#\s*REQUIRES:\s*(.+)", code)
            if requires_match:
                deps = [d.strip() for d in requires_match.group(1).split(",")]
                dependencies.extend(deps)

            # Filter out built-in modules
            builtin_modules = {
                "os",
                "sys",
                "time",
                "datetime",
                "json",
                "csv",
                "re",
                "collections",
                "itertools",
                "functools",
                "math",
                "random",
                "logging",
                "typing",
            }
            # Filter out builtins and obvious invalid values
            dependencies = [d for d in dependencies if d and str(d).strip() and str(d).strip() not in builtin_modules and not str(d).strip().lower().startswith("none")]

            # Map common module names to pip package names
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

            normalized = []
            for d in dependencies:
                # If it's already a package string with version/spec, keep as-is
                if isinstance(d, str) and ("==" in d or ">=" in d or "<=" in d):
                    normalized.append(d)
                    continue

                name = str(d).strip()
                # If dotted import like "scipy.stats", take first segment
                top = name.split(".")[0]
                pip_name = module_to_pip.get(top, top)
                if pip_name not in normalized:
                    normalized.append(pip_name)

            # Remove duplicates while preserving order
            seen = set()
            deduped = []
            for dep in normalized:
                if dep not in seen:
                    deduped.append(dep)
                    seen.add(dep)

            dependencies = deduped

        elif language == ProgrammingLanguage.JAVA:
            import re

            # Look for REQUIRES comment with Maven coordinates
            requires_match = re.search(r"//\s*REQUIRES:\s*(.+)", code)
            if requires_match:
                # Parse Maven coordinates: groupId:artifactId:version
                deps_text = requires_match.group(1)
                for dep_str in deps_text.split(","):
                    dep_str = dep_str.strip()
                    parts = dep_str.split(":")
                    if len(parts) == 3:
                        dependencies.append(
                            {"groupId": parts[0], "artifactId": parts[1], "version": parts[2]}
                        )

            # Also extract from imports for auto-detection
            imports = re.findall(r"^import\s+([\w.]+);", code, re.MULTILINE)

            # Map common imports to Maven dependencies
            import_to_maven = {
                "com.google.gson": {
                    "groupId": "com.google.code.gson",
                    "artifactId": "gson",
                    "version": "2.10.1",
                },
                "org.apache.http": {
                    "groupId": "org.apache.httpcomponents.client5",
                    "artifactId": "httpclient5",
                    "version": "5.3",
                },
                "org.json": {"groupId": "org.json", "artifactId": "json", "version": "20231013"},
                "com.fasterxml.jackson": {
                    "groupId": "com.fasterxml.jackson.core",
                    "artifactId": "jackson-databind",
                    "version": "2.16.0",
                },
            }

            for imp in imports:
                if imp.startswith("java.") or imp.startswith("javax."):
                    continue
                for prefix, maven_dep in import_to_maven.items():
                    if imp.startswith(prefix):
                        if maven_dep not in dependencies:
                            dependencies.append(maven_dep)
                        break

        return dependencies

    def _generate_filename(self, language: ProgrammingLanguage, code: str = "") -> str:
        """Generate appropriate filename based on language."""
        import datetime
        import re

        if language == ProgrammingLanguage.PYTHON:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"generated_script_{timestamp}.py"
        elif language == ProgrammingLanguage.JAVA:
            # Try to extract class name from code
            if code:
                class_match = re.search(r"public\s+class\s+(\w+)", code)
                if class_match:
                    return f"{class_match.group(1)}.java"
            # Fallback to timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"GeneratedClass_{timestamp}.java"

        return f"generated_code.txt"
