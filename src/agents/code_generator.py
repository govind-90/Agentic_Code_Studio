"""Code generation agent using LangChain."""

from typing import Dict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from src.config.prompts import CODE_GENERATOR_HUMAN_TEMPLATE, CODE_GENERATOR_SYSTEM_PROMPT
from src.config.settings import settings
from src.models.schemas import ProgrammingLanguage
from src.utils.logger import code_gen_logger as logger


class CodeGeneratorAgent:
    """Agent responsible for generating code from requirements."""

    # def __init__(self):
    #     """Initialize the code generator agent."""
    #     self.llm = ChatGoogleGenerativeAI(
    #         model=settings.llm_model_name,
    #         google_api_key=settings.google_api_key,
    #         temperature=settings.agent_temperature,
    #         convert_system_message_to_human=True,
    #     )

    #     logger.info("Code Generator Agent initialized")

    def __init__(self):
        """Initialize the code generator agent."""
        self.llm = ChatGroq(
            model=settings.llm_model_name_groq,
            groq_api_key=settings.groq_api_key,
            temperature=settings.agent_temperature,
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
                # Filter out empty strings and comment-like entries
                deps = [d for d in deps if d and not d.startswith("#")]
                dependencies.extend(deps)

            # Filter out built-in modules AND project-internal imports
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
                "unittest",
                "pathlib",
                "io",
                "subprocess",
                "tempfile",
                "shutil",
                "copy",
                "pickle",
                "threading",
                "multiprocessing",
                "argparse",
                "configparser",
                "email",
                "urllib",
                "http",
                "socket",
                "ssl",
                "asyncio",
                "hashlib",
                "hmac",
                "secrets",
                "uuid",
                "enum",
                "dataclasses",
                "abc",
                "sqlite3",
                "dbm",
                "shelve",
            }
            
            # Common project-internal package names to exclude
            project_modules = {
                "src",
                "app",
                "tests",
                "test",
                "config",
                "utils",
                "models",
                "schemas",
                "database",
                "api",
                "core",
                "services",
                "controllers",
                "views",
                "main",
            }
            
            # Filter out builtins, project modules, and invalid values
            dependencies = [
                d for d in dependencies 
                if d and str(d).strip() 
                and str(d).strip().lower() not in builtin_modules 
                and str(d).strip().lower() not in project_modules
                and not str(d).strip().lower().startswith("none")
            ]

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

    def _convert_javax_to_jakarta(self, code: str) -> bool:
        """
        Convert javax.* imports to jakarta.* for Spring Boot 3.x compatibility.
        
        IMPORTANT: Does NOT convert javax.sql.* - it's part of the JDK (java.sql namespace)
        and should remain as javax.sql
        
        Returns True if any conversions were made.
        """
        import re
        
        # Map of javax packages that need to be converted to jakarta
        # NOTE: javax.sql is NOT included - it's a JDK built-in package
        conversions = {
            'javax.persistence': 'jakarta.persistence',
            'javax.validation': 'jakarta.validation',
            'javax.servlet': 'jakarta.servlet',
            'javax.transaction': 'jakarta.transaction',
            'javax.ejb': 'jakarta.ejb',
            'javax.annotation': 'jakarta.annotation',
            'javax.inject': 'jakarta.inject',
            'javax.ws.rs': 'jakarta.ws.rs',
            'javax.jms': 'jakarta.jms',
            'javax.mail': 'jakarta.mail',
        }
        
        original_code = code
        conversion_count = 0
        
        for javax_pkg, jakarta_pkg in conversions.items():
            # Replace import statements
            pattern = rf'\bimport\s+{re.escape(javax_pkg)}\b'
            if re.search(pattern, code):
                code = re.sub(pattern, f'import {jakarta_pkg}', code)
                conversion_count += 1
        
        if conversion_count > 0:
            logger.info(f"Converted {conversion_count} javax.* imports to jakarta.*")
        
        return code

    def generate_project_code(
        self,
        requirements: str,
        language: ProgrammingLanguage,
        project_template: str,
        template_structure: dict,
        error_context: str = ""
    ) -> Dict[str, any]:
        """
        Generate code for a multi-file project based on template structure.

        Args:
            requirements: User's natural language requirements
            language: Target programming language
            project_template: Template name (fastapi, spring_boot, etc.)
            template_structure: Dict defining the file structure from template
            error_context: Optional context from previous failed attempts

        Returns:
            Generated code files and metadata
        """
        try:
            logger.info(f"Generating multi-file {language.value} project with template {project_template}")

            # Build file list from template structure
            def extract_file_paths(structure, prefix=""):
                files = []
                for key, value in structure.items():
                    path = f"{prefix}/{key}" if prefix else key
                    if isinstance(value, dict):
                        files.extend(extract_file_paths(value, path))
                    else:
                        # It's a file
                        files.append(path)
                return files

            file_list = extract_file_paths(template_structure)

            # Enhanced prompt for multi-file generation
            prompt_text = f"""{CODE_GENERATOR_SYSTEM_PROMPT}

**MULTI-FILE PROJECT GENERATION:**

You MUST generate code for ALL files listed below. This is a {project_template} project.

**Required Files:**
{chr(10).join(f"- {f}" for f in file_list)}

**CRITICAL INSTRUCTIONS:**
1. Generate COMPLETE, WORKING code for EACH file listed above
2. Use this exact format for EACH file:

# FILE: <exact_filename_from_list>
```{language.value}
<complete working code here>
```

3. ENSURE ALL CODE IS COMPLETE:
   - Every opening brace {{ must have a closing brace }}
   - Every class/interface/method must be fully implemented
   - No truncated or incomplete code blocks
   
4. Files must work together - ensure proper imports and dependencies
5. Include ALL necessary error handling, logging, and best practices
6. For configuration files (requirements.txt, pom.xml), include ALL dependencies
7. Do NOT skip any files - generate content for ALL files listed
8. End each code block with ``` to mark completion

"""

            prompt_text += f"""
**User Requirements:**
{requirements}

**Target Language:** {language.value.upper()}

**CRITICAL FOR SPRING BOOT - READ CAREFULLY:**
- DO NOT create ApplicationConfig.java or any manual DataSource configuration
- DO NOT create @Configuration classes for database setup
- Spring Boot auto-configures everything via application.properties
- DO NOT use Jakarta CDI annotations (@ApplicationScoped, @Produces, @Inject)  
- DO NOT use Apache Commons DBCP2 or manual connection pools
- USE ONLY Spring annotations: @RestController, @Service, @Repository, @Autowired, @Entity
- Generate ONLY: Entity, Repository, Service, Controller classes + application.properties
- Database config goes in application.properties (spring.datasource.url, etc.)
- Focus on core CRUD functionality - keep it simple
- Only add security/authentication if EXPLICITLY requested by user
- Note: javax.sql.DataSource is JDK built-in, never convert to jakarta.sql

{error_context if error_context else ""}

Generate COMPLETE code for ALL files now (use # FILE: filename format):"""

            # Generate code using LLM
            response = self.llm.invoke(prompt_text)
            generated_code = response.content

            # Handle different response formats
            if isinstance(generated_code, list):
                text_parts = []
                for item in generated_code:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    else:
                        text_parts.append(str(item))
                generated_code = "\n".join(text_parts)
            else:
                generated_code = str(generated_code) if generated_code else ""

            # Extract dependencies
            dependencies = self._extract_dependencies(generated_code, language)

            # Parse multi-file output
            import re

            files = []

            # Look for FILE markers
            file_marker_pattern = re.compile(r"(?m)^#\s*FILE:\s*(.+)$", re.IGNORECASE)
            markers = list(file_marker_pattern.finditer(generated_code))

            if markers:
                logger.info(f"Found {len(markers)} FILE markers")
                seen_files = {}  # Track files by filename to deduplicate
                
                for i, m in enumerate(markers):
                    filename = m.group(1).strip()
                    start = m.end()
                    end = markers[i + 1].start() if i + 1 < len(markers) else len(generated_code)
                    content = generated_code[start:end].strip()

                    # Remove code fences
                    content = re.sub(r"^```[\w]*\n", "", content)
                    content = re.sub(r"\n```$", "", content)
                    content = content.strip()

                    if content:
                        # For Java files, apply fixes
                        if filename.endswith('.java') and language == ProgrammingLanguage.JAVA:
                            # Fix 1: Convert javax.* to jakarta.* for Spring Boot 3.x compatibility
                            content = self._convert_javax_to_jakarta(content)
                            
                            # Fix 2: Check for balanced braces
                            open_braces = content.count('{')
                            close_braces = content.count('}')
                            if open_braces != close_braces:
                                logger.warning(f"Unbalanced braces in {filename}: {open_braces} open, {close_braces} close")
                                # Try to fix by adding missing closing braces
                                if open_braces > close_braces:
                                    missing = open_braces - close_braces
                                    content += '\n' + ('}\n' * missing)
                                    logger.info(f"Added {missing} closing braces to {filename}")
                        
                        # Deduplicate: keep the last occurrence (usually most complete)
                        if filename in seen_files:
                            logger.warning(f"Duplicate file detected: {filename}, keeping latest version")
                        seen_files[filename] = {"filename": filename, "code": content}
                        logger.info(f"Extracted file: {filename} ({len(content)} chars)")
                
                # Convert dict to list
                files = list(seen_files.values())
            else:
                # Fallback: try to find code blocks
                logger.warning("No FILE markers found, trying to extract code blocks")
                code_blocks = re.findall(r"```(?:\w+)?\n(.+?)```", generated_code, re.DOTALL)

                for idx, block in enumerate(code_blocks):
                    # Try to match with template files
                    filename = file_list[idx] if idx < len(file_list) else f"generated_{idx}.{language.value}"
                    files.append({"filename": filename, "code": block.strip()})

            if not files:
                logger.error("Failed to extract any files from LLM response")
                return {
                    "success": False,
                    "error": "Failed to parse multi-file response from LLM"
                }

            logger.info(f"Successfully generated {len(files)} files with {len(dependencies)} dependencies")

            return {
                "success": True,
                "files": files,
                "language": language.value,
                "dependencies": dependencies,
            }

        except Exception as e:
            logger.error(f"Multi-file code generation failed: {str(e)}")
            return {"success": False, "error": str(e)}

