"""Orchestrator agent that coordinates all other agents."""

import time
from datetime import datetime
from typing import Callable, Dict, Optional

from src.agents.build_agent import BuildAgent
from src.agents.code_generator import CodeGeneratorAgent
from src.agents.testing_agent import TestingAgent
from src.config.settings import settings
from src.models.schemas import (
    AgentStatus,
    CodeArtifact,
    ErrorType,
    GenerationSession,
    IterationLog,
    ProgrammingLanguage,
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

            iteration_log.code_gen_status = AgentStatus.SUCCESS
            iteration_log.generated_code = code_result["code"]

            generated_code = code_result["code"]
            dependencies = code_result["dependencies"]

            logger.info(f"Code generated successfully with {len(dependencies)} dependencies")

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
                filename=code_result["filename"],
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

            # Save metadata
            metadata_file = session_dir / "metadata.json"
            metadata_file.write_text(session.model_dump_json(indent=2), encoding="utf-8")

            # Save final code if successful
            if session.final_code:
                code_file = session_dir / session.final_code.filename
                code_file.write_text(session.final_code.code, encoding="utf-8")

            logger.info(f"Session saved to {session_dir}")

        except Exception as e:
            logger.error(f"Failed to save session: {str(e)}")

    @staticmethod
    def load_session(session_id: str) -> Optional[GenerationSession]:
        """Load a previous session from disk."""
        try:
            from pathlib import Path

            session_dir = Path(settings.session_storage_path) / session_id
            metadata_file = session_dir / "metadata.json"

            if not metadata_file.exists():
                return None

            session_data = metadata_file.read_text()
            return GenerationSession.model_validate_json(session_data)

        except Exception as e:
            logger.error(f"Failed to load session: {str(e)}")
            return None

    @staticmethod
    def list_sessions() -> list:
        """List all saved sessions."""
        try:
            from pathlib import Path

            session_root = Path(settings.session_storage_path)

            if not session_root.exists():
                return []

            sessions = []
            for session_dir in session_root.iterdir():
                if session_dir.is_dir():
                    metadata_file = session_dir / "metadata.json"
                    if metadata_file.exists():
                        session = GenerationSession.model_validate_json(metadata_file.read_text())
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

            # Sort by creation time, newest first
            sessions.sort(key=lambda x: x["created_at"], reverse=True)
            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}")
            return []
