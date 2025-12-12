"""Orchestrator agent that coordinates all other agents."""

import time
import json
from datetime import datetime
from typing import Callable, Dict, Optional

from src.agents.build_agent import BuildAgent
from src.agents.code_generator import CodeGeneratorAgent
from src.agents.project_scaffold import ProjectScaffoldAgent
from src.agents.project_validator import ProjectValidatorAgent
from src.agents.testing_agent import TestingAgent
from src.config.settings import settings
from src.models.schemas import (
    AgentStatus,
    CodeArtifact,
    ErrorType,
    FileArtifact,
    GenerationSession,
    IterationLog,
    ProgrammingLanguage,
    ProjectSession,
)
from src.utils.error_parser import ErrorParser
from src.utils.logger import orchestrator_logger as logger


class OrchestratorAgent:
    """Main orchestrator that manages the multi-agent workflow."""

    def __init__(self):
        """Initialize orchestrator and all sub-agents."""
        self.code_generator = CodeGeneratorAgent()
        self.build_agent = BuildAgent()
        self.testing_agent = TestingAgent()
        self.project_scaffold = ProjectScaffoldAgent()
        self.project_validator = ProjectValidatorAgent()
        self.error_parser = ErrorParser()

        logger.info("Orchestrator Agent initialized")

    def generate_code(
        self,
        requirements: str,
        language: ProgrammingLanguage,
        max_iterations: int = None,
        runtime_credentials: Dict[str, str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> GenerationSession:
        """
        Main workflow: Generate, build, and test code iteratively.

        Args:
            requirements: User's natural language requirements
            language: Target programming language
            max_iterations: Maximum retry attempts
            runtime_credentials: Optional runtime credentials (API keys, etc.)
            progress_callback: Optional callback for UI updates

        Returns:
            GenerationSession with complete history and results
        """
        # Initialize session
        import uuid

        session = GenerationSession(
            session_id=str(uuid.uuid4())[:8],
            requirements=requirements,
            language=language,
            max_iterations=max_iterations or settings.max_iterations,
            runtime_credentials=runtime_credentials or {},
        )

        logger.info(f"Starting code generation session {session.session_id}")
        start_time = time.time()

        error_context = ""

        for iteration in range(1, session.max_iterations + 1):
            logger.info(f"=== Iteration {iteration}/{session.max_iterations} ===")

            iteration_log = IterationLog(iteration_number=iteration)
            session.current_iteration = iteration

            # Update progress
            if progress_callback:
                progress_callback(f"Iteration {iteration}: Generating code...", iteration)

            # STEP 1: Code Generation
            iteration_log.code_gen_status = AgentStatus.RUNNING
            logger.info("Step 1: Code Generation")

            code_result = self.code_generator.generate_code(
                requirements=requirements, language=language, error_context=error_context
            )

            if not code_result.get("success"):
                iteration_log.code_gen_status = AgentStatus.FAILED
                iteration_log.error_message = code_result.get("error")
                session.iterations.append(iteration_log)
                continue

            # Normalize code output (LLM may return a list of files instead of a single code blob)
            files = code_result.get("files") or []
            generated_code = code_result.get("code")
            filename = code_result.get("filename")
            dependencies = code_result.get("dependencies", [])

            if not generated_code and files:
                first_file = files[0]
                generated_code = first_file.get("code")
                filename = filename or first_file.get("filename")

            if not generated_code:
                iteration_log.code_gen_status = AgentStatus.FAILED
                iteration_log.error_type = ErrorType.LOGIC
                iteration_log.error_message = "Code generator did not return code."
                session.iterations.append(iteration_log)
                continue

            if not filename:
                filename = f"generated_code.{ 'py' if language == ProgrammingLanguage.PYTHON else 'java' }"

            iteration_log.code_gen_status = AgentStatus.SUCCESS
            iteration_log.generated_code = generated_code

            logger.info(f"Code generated successfully with {len(dependencies)} dependencies")
            
            # Update UI with code generation completion
            if progress_callback:
                progress_callback(f"Iteration {iteration}: Code generated ✓", iteration)

            # STEP 2: Build & Compile
            if progress_callback:
                progress_callback(f"Iteration {iteration}: Building code...", iteration)

            iteration_log.build_status = AgentStatus.RUNNING
            logger.info("Step 2: Build & Compile")

            build_result = self.build_agent.analyze_and_build(
                code=generated_code, language=language, dependencies=dependencies
            )

            iteration_log.build_result = build_result

            if build_result.status != "success":
                logger.warning("Build failed, analyzing errors...")
                iteration_log.build_status = AgentStatus.FAILED

                # Parse errors and create context for next iteration
                # Ensure we pass a string even if errors contain non-string items
                error_info = self.error_parser.parse_error(
                    error_message="\n".join(str(x) for x in build_result.errors),
                    language=language.value,
                    code=generated_code,
                )

                iteration_log.error_type = error_info["error_type"]
                iteration_log.error_message = error_info["root_cause"]

                # Check for missing credentials
                if error_info["missing_credentials"]:
                    session.missing_credentials = error_info["missing_credentials"]
                    logger.info(f"Missing credentials detected: {session.missing_credentials}")
                    # In real scenario, this would pause and wait for user input

                error_context = self.error_parser.format_error_context(
                    error_info, iteration, session.max_iterations
                )

                session.iterations.append(iteration_log)
                continue

            iteration_log.build_status = AgentStatus.SUCCESS
            logger.info("Build successful")
            
            # Update UI with build completion
            if progress_callback:
                progress_callback(f"Iteration {iteration}: Build successful ✓", iteration)

            # STEP 3: Testing
            if progress_callback:
                progress_callback(f"Iteration {iteration}: Testing code...", iteration)

            iteration_log.test_status = AgentStatus.RUNNING
            logger.info("Step 3: Testing & Validation")

            test_result = self.testing_agent.execute_and_test(
                requirements=requirements,
                code=generated_code,
                language=language,
                runtime_credentials=session.runtime_credentials,
            )

            iteration_log.test_result = test_result

            if test_result.status != "pass":
                logger.warning("Tests failed, analyzing issues...")
                iteration_log.test_status = AgentStatus.FAILED

                # Parse test failures
                error_message = "\n".join(str(x) for x in (test_result.issues_found + [test_result.execution_logs]))
                error_info = self.error_parser.parse_error(
                    error_message=error_message, language=language.value, code=generated_code
                )

                iteration_log.error_type = error_info["error_type"]
                iteration_log.error_message = error_info["root_cause"]

                error_context = self.error_parser.format_error_context(
                    error_info, iteration, session.max_iterations
                )

                session.iterations.append(iteration_log)
                continue

            iteration_log.test_status = AgentStatus.SUCCESS
            logger.info("✅ All tests passed!")

            # SUCCESS!
            session.status = AgentStatus.SUCCESS
            session.success = True
            session.final_code = CodeArtifact(
                language=language,
                code=generated_code,
                filename=filename,
                # Ensure dependencies are strings for UI and serialization
                dependencies=[
                    (d if isinstance(d, str) else f"{d.get('groupId')}:{d.get('artifactId')}:{d.get('version')}" if isinstance(d, dict) else str(d))
                    for d in dependencies
                ],
            )
            session.iterations.append(iteration_log)

            break  # Exit loop on success

        # Finalize session
        session.total_execution_time = time.time() - start_time
        session.updated_at = datetime.now()

        if not session.success:
            session.status = AgentStatus.FAILED
            logger.warning(
                f"Failed to generate working code after {session.max_iterations} iterations"
            )
        else:
            logger.info(f"✅ Code generation successful in {iteration} iteration(s)")

        # Save session if persistence enabled
        if settings.enable_session_persistence:
            self._save_session(session)

        return session

    def _save_session(self, session: GenerationSession):
        """Save session to disk for history."""
        try:
            from pathlib import Path
            import json

            session_dir = Path(settings.session_storage_path) / session.session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Saving session {session.session_id} to {session_dir}")

            # Save metadata
            metadata_file = session_dir / "metadata.json"
            metadata = session.model_dump_json(indent=2)
            metadata_file.write_text(metadata, encoding="utf-8")
            logger.info(f"✓ Saved metadata: {metadata_file}")

            # Save final code if successful
            if session.final_code:
                code_file = session_dir / session.final_code.filename
                code_file.write_text(session.final_code.code, encoding="utf-8")
                logger.info(f"✓ Saved code: {code_file}")

            logger.info(f"✅ Session {session.session_id} saved successfully")

        except Exception as e:
            logger.error(f"❌ Failed to save session: {str(e)}", exc_info=True)

    @staticmethod
    def load_session(session_id: str) -> Optional[GenerationSession]:
        """Load a previous session from disk."""
        try:
            from pathlib import Path

            session_dir = Path(settings.session_storage_path) / session_id
            metadata_file = session_dir / "metadata.json"

            if not metadata_file.exists():
                return None

            raw = metadata_file.read_text(encoding='utf-8')
            data = json.loads(raw)

            # Normalize legacy/unknown error_type values to avoid validation failures
            allowed_error_types = {et.value for et in ErrorType}
            for iteration in data.get("iterations", []):
                et = iteration.get("error_type")
                if et and et not in allowed_error_types:
                    iteration["error_type"] = ErrorType.LOGIC.value

            return GenerationSession.model_validate(data)

        except Exception as e:
            logger.error(f"Failed to load session: {str(e)}")
            return None

    @staticmethod
    def list_sessions() -> list:
        """List all saved sessions."""
        try:
            from pathlib import Path

            session_root = Path(settings.session_storage_path)
            
            logger.info(f"Looking for sessions in: {session_root.absolute()}")

            if not session_root.exists():
                logger.warning(f"Session directory does not exist: {session_root.absolute()}")
                return []

            sessions = []
            session_count = 0
            for session_dir in session_root.iterdir():
                session_count += 1
                if not session_dir.is_dir():
                    logger.debug(f"Skipping non-directory: {session_dir.name}")
                    continue
                    
                metadata_file = session_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        raw = metadata_file.read_text(encoding='utf-8')
                        data = json.loads(raw)

                        allowed_error_types = {et.value for et in ErrorType}
                        for iteration in data.get("iterations", []):
                            et = iteration.get("error_type")
                            if et and et not in allowed_error_types:
                                iteration["error_type"] = ErrorType.LOGIC.value

                        session = GenerationSession.model_validate(data)
                        sessions.append(
                            {
                                "session_id": session.session_id,
                                "requirements": (
                                    session.requirements[:100] + "..."
                                    if len(session.requirements) > 100
                                    else session.requirements
                                ),
                                "language": session.language.value,
                                "success": session.success,
                                "created_at": session.created_at,
                            }
                        )
                        logger.debug(f"✓ Loaded session {session.session_id}")
                    except Exception as e:
                        logger.error(f"✗ Failed to load session from {session_dir.name}: {e}", exc_info=True)
                        continue
                else:
                    logger.debug(f"No metadata.json in {session_dir.name}")

            logger.info(f"Found {session_count} items in session directory, loaded {len(sessions)} valid sessions")
            
            # Sort by creation time, newest first
            sessions.sort(key=lambda x: x["created_at"], reverse=True)
            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}", exc_info=True)
            return []

    def generate_project(
        self,
        requirements: str,
        project_name: str,
        project_template: str,
        language: ProgrammingLanguage,
        max_iterations: int = None,
        runtime_credentials: Dict[str, str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> ProjectSession:
        """
        Generate a multi-file project iteratively.

        Args:
            requirements: User's natural language requirements
            project_name: Name of the project
            project_template: Template to use (fastapi, spring_boot, python_package)
            language: Target programming language
            max_iterations: Maximum retry attempts
            runtime_credentials: Optional runtime credentials
            progress_callback: Callback for progress updates

        Returns:
            ProjectSession with generated files and build status
        """
        import uuid

        session_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Create session
        session = ProjectSession(
            session_id=session_id,
            requirements=requirements,
            language=language,
            project_name=project_name,
            project_template=project_template,
            max_iterations=max_iterations or settings.max_iterations,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        logger.info(
            f"Starting project generation (ID: {session_id}, Template: {project_template})"
        )

        # STEP 1: Scaffold project structure
        if progress_callback:
            progress_callback("Scaffolding project structure...", 0)

        logger.info("Step 1: Scaffold Project")

        try:
            scaffold_result = self.project_scaffold.scaffold_project(
                project_name=project_name,
                template_name=project_template,
                root_dir=None,
            )

            if not scaffold_result.get("success"):
                logger.error(f"Project scaffolding failed")
                session.status = AgentStatus.FAILED
                session.success = False
                return session

            session.root_dir = scaffold_result.get("project_root")
            session.file_tree = scaffold_result.get("file_tree")

            logger.info(
                f"Project scaffolded successfully at {session.root_dir}"
            )

        except Exception as e:
            logger.error(f"Scaffolding error: {str(e)}")
            session.status = AgentStatus.FAILED
            session.success = False
            return session

        # STEP 2: Iterative code generation, validation, and build
        for iteration in range(1, session.max_iterations + 1):
            iteration_log = IterationLog(iteration_number=iteration)
            logger.info(f"\n{'='*60}")
            logger.info(f"Iteration {iteration}/{session.max_iterations}")
            logger.info(f"{'='*60}")

            # Generate code for all files
            if progress_callback:
                progress_callback(
                    f"Iteration {iteration}: Generating code...", iteration
                )

            logger.info("Step 2: Multi-file Code Generation")
            iteration_log.code_gen_status = AgentStatus.RUNNING

            # Get template structure for multi-file generation
            from src.config.project_templates import get_template
            template = get_template(project_template)
            template_structure = template.get("structure", {}) if template else {}

            # Use project-specific generation method
            code_result = self.code_generator.generate_project_code(
                requirements=requirements,
                language=language,
                project_template=project_template,
                template_structure=template_structure,
                error_context=iteration_log.error_message if iteration > 1 else "",
            )

            generated_files = code_result.get("files", [])
            dependencies = code_result.get("dependencies", [])

            if not generated_files:
                logger.warning("No files generated")
                iteration_log.code_gen_status = AgentStatus.FAILED
                session.iterations.append(iteration_log)
                continue

            # Convert generated code to FileArtifact objects
            # Detect file language based on extension, not just the project language
            def get_file_language(filename):
                """Infer file language from filename extension."""
                if filename.endswith(('.py', 'requirements.txt')):
                    return 'python'
                elif filename.endswith(('.java', 'pom.xml')):
                    return 'java'
                elif filename.endswith(('.yml', '.yaml', 'Dockerfile', 'docker-compose.yml')):
                    return 'yaml'  # or treat as non-code
                else:
                    return language.value  # fallback to project language
            
            files_to_validate = [
                FileArtifact(
                    filename=f.get("filename", f"file_{i}.{language.value}"),
                    code=f.get("code", ""),
                    language=get_file_language(f.get("filename", f"file_{i}.{language.value}")),
                    size=len(f.get("code", "")),
                    filepath=f"{session.root_dir}/{f.get('filename', f'file_{i}.{language.value}')}",
                )
                for i, f in enumerate(generated_files)
            ]

            session.files = files_to_validate
            session.all_dependencies = dependencies

            iteration_log.code_gen_status = AgentStatus.SUCCESS
            logger.info(
                f"Generated {len(files_to_validate)} files with {len(dependencies)} dependencies"
            )

            # STEP 3: Project Validation
            if progress_callback:
                progress_callback(f"Iteration {iteration}: Validating project...", iteration)

            logger.info("Step 3: Project Validation")
            iteration_log.build_status = AgentStatus.RUNNING

            validation_result = self.project_validator.validate_project(
                files=files_to_validate, language=language
            )

            if not validation_result.get("success"):
                logger.warning("Validation failed, analyzing errors...")
                iteration_log.build_status = AgentStatus.FAILED
                iteration_log.error_type = "logic"
                iteration_log.error_message = "\n".join(
                    validation_result.get("errors", [])
                )

                session.iterations.append(iteration_log)
                continue

            iteration_log.build_status = AgentStatus.SUCCESS
            logger.info("Project validation successful")

            # STEP 4: Build Project
            if progress_callback:
                progress_callback(f"Iteration {iteration}: Building project...", iteration)

            logger.info("Step 4: Project Build")

            build_result = self.build_agent.build_project(
                files=files_to_validate,
                language=language,
                dependencies=dependencies,
                root_dir=session.root_dir,
            )

            if build_result.status != "success":
                logger.warning("Build failed, analyzing errors...")
                iteration_log.build_status = AgentStatus.FAILED
                iteration_log.error_message = "\n".join(build_result.errors)

                session.iterations.append(iteration_log)
                continue

            iteration_log.build_status = AgentStatus.SUCCESS
            logger.info("Project build successful")

            # STEP 5: Test Project
            if progress_callback:
                progress_callback(f"Iteration {iteration}: Testing project...", iteration)

            logger.info("Step 5: Project Testing")
            iteration_log.test_status = AgentStatus.RUNNING

            test_result = self.testing_agent.test_project(
                requirements=requirements,
                files=files_to_validate,
                language=language,
                root_dir=session.root_dir,
                runtime_credentials=runtime_credentials,
            )

            if test_result.status != "pass":
                logger.warning("Tests failed")
                iteration_log.test_status = AgentStatus.FAILED
                iteration_log.test_result = test_result

                session.iterations.append(iteration_log)
                continue

            iteration_log.test_status = AgentStatus.SUCCESS
            logger.info("✅ All tests passed")

            # Success!
            session.success = True
            session.status = AgentStatus.SUCCESS
            session.iterations.append(iteration_log)

            break

        # Finalize session
        session.total_execution_time = time.time() - start_time
        session.updated_at = datetime.now()

        if not session.success:
            session.status = AgentStatus.FAILED
            logger.warning(
                f"Failed to generate project after {session.max_iterations} iterations"
            )
        else:
            logger.info(
                f"✅ Project generation successful in {len(session.iterations)} iteration(s)"
            )

        # Save session if persistence enabled
        if settings.enable_session_persistence:
            self._save_project_session(session)

        return session

    def _save_project_session(self, session: ProjectSession):
        """Save project session to disk."""
        try:
            from pathlib import Path
            import json

            session_dir = Path(settings.session_storage_path) / session.session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Saving project session {session.session_id} to {session_dir}")

            # Save metadata
            metadata_file = session_dir / "metadata.json"
            metadata = session.model_dump_json(indent=2)
            metadata_file.write_text(metadata, encoding="utf-8")
            logger.info(f"✓ Saved project metadata: {metadata_file}")

            # Save all files
            files_dir = session_dir / "files"
            files_dir.mkdir(parents=True, exist_ok=True)

            for file in session.files:
                file_path = files_dir / file.filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file.code, encoding="utf-8")
            
            logger.info(f"✓ Saved {len(session.files)} project files")
            logger.info(f"✅ Project session {session.session_id} saved successfully")

        except Exception as e:
            logger.error(f"❌ Failed to save project session: {str(e)}", exc_info=True)
