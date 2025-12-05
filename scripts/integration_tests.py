"""Integration testing script for Phase 3 - Multi-file project generation."""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.orchestrator import OrchestratorAgent
from src.models.schemas import ProgrammingLanguage
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def test_fastapi_todo_api():
    """Test 1: FastAPI TODO API generation."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: FastAPI TODO API Generation")
    logger.info("="*80)

    requirements = """
    Create a FastAPI REST API for a TODO application with:
    - SQLAlchemy database models for todos and users
    - Pydantic schemas for request/response validation
    - CRUD endpoints for todos (create, read, update, delete)
    - User authentication with JWT tokens
    - Database initialization and connection pooling
    - Unit tests with pytest
    - Docker support with Dockerfile
    - GitHub Actions CI/CD workflow
    Ensure all files have proper imports, the project structure is clean, 
    and all dependencies are correctly specified.
    """

    orchestrator = OrchestratorAgent()

    try:
        start_time = time.time()

        session = orchestrator.generate_project(
            requirements=requirements.strip(),
            project_name="todo_app",
            project_template="fastapi",
            language=ProgrammingLanguage.PYTHON,
            max_iterations=3,
        )

        duration = time.time() - start_time

        # Check results
        logger.info(f"\nFastAPI Project Generation Results:")
        logger.info(f"  Status: {'✅ SUCCESS' if session.success else '❌ FAILED'}")
        logger.info(f"  Iterations: {len(session.iterations)}")
        logger.info(f"  Files Generated: {len(session.files) if hasattr(session, 'files') else 0}")
        logger.info(f"  Dependencies: {len(session.all_dependencies) if hasattr(session, 'all_dependencies') else 0}")
        logger.info(f"  Duration: {duration:.2f}s")

        if session.files:
            logger.info(f"\n  Generated Files:")
            for file in session.files:
                logger.info(f"    - {file.filename} ({len(file.code)} bytes)")

        if session.all_dependencies:
            logger.info(f"\n  Dependencies:")
            for dep in session.all_dependencies:
                logger.info(f"    - {dep}")

        # Detailed iteration logs
        for i, iter_log in enumerate(session.iterations, 1):
            iteration_label = getattr(iter_log, 'iteration_number', i)
            logger.info(f"\n  Iteration {iteration_label}:")
            gen_status = getattr(iter_log, 'code_gen_status', getattr(iter_log, 'generation_status', 'UNKNOWN'))
            build_status = getattr(iter_log, 'build_status', 'UNKNOWN')
            test_status = getattr(iter_log, 'test_status', 'UNKNOWN')
            logger.info(f"    Generation: {gen_status}")
            logger.info(f"    Build: {build_status}")
            logger.info(f"    Test: {test_status}")
            if getattr(iter_log, 'error_message', None):
                logger.warning(f"    Error: {iter_log.error_message[:200]}")

        return session.success

    except Exception as e:
        logger.error(f"FastAPI test failed: {str(e)}", exc_info=True)
        return False


def test_spring_boot_auth():
    """Test 2: Spring Boot Authentication Microservice generation."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Spring Boot Auth Microservice Generation")
    logger.info("="*80)

    requirements = """
    Create a Spring Boot 3.1.5 microservice for user authentication:
    - Spring Security with JWT token-based authentication
    - UserController REST endpoints for registration and login
    - AuthService with password hashing and JWT generation
    - User JPA entity with email and password fields
    - UserRepository for database access
    - JwtUtil utility class for token creation and validation
    - SecurityConfig for Spring Security configuration
    - JUnit test cases for controller and service
    - MySQL database support with JDBC driver
    - Docker and docker-compose files
    - application.yml configuration with MySQL connection
    Ensure proper Java package structure (com.example.*), 
    all classes have correct dependencies, and tests validate authentication flow.
    """

    orchestrator = OrchestratorAgent()

    try:
        start_time = time.time()

        session = orchestrator.generate_project(
            requirements=requirements.strip(),
            project_name="auth_service",
            project_template="spring_boot",
            language=ProgrammingLanguage.JAVA,
            max_iterations=3,
        )

        duration = time.time() - start_time

        # Check results
        logger.info(f"\nSpring Boot Project Generation Results:")
        logger.info(f"  Status: {'✅ SUCCESS' if session.success else '❌ FAILED'}")
        logger.info(f"  Iterations: {len(session.iterations)}")
        logger.info(f"  Files Generated: {len(session.files) if hasattr(session, 'files') else 0}")
        logger.info(f"  Dependencies: {len(session.all_dependencies) if hasattr(session, 'all_dependencies') else 0}")
        logger.info(f"  Duration: {duration:.2f}s")

        if session.files:
            logger.info(f"\n  Generated Files:")
            for file in session.files:
                logger.info(f"    - {file.filename} ({len(file.code)} bytes)")

        if session.all_dependencies:
            logger.info(f"\n  Dependencies:")
            for dep in session.all_dependencies:
                logger.info(f"    - {dep}")

        # Detailed iteration logs
        for i, iter_log in enumerate(session.iterations, 1):
            iteration_label = getattr(iter_log, 'iteration_number', i)
            logger.info(f"\n  Iteration {iteration_label}:")
            gen_status = getattr(iter_log, 'code_gen_status', getattr(iter_log, 'generation_status', 'UNKNOWN'))
            build_status = getattr(iter_log, 'build_status', 'UNKNOWN')
            test_status = getattr(iter_log, 'test_status', 'UNKNOWN')
            logger.info(f"    Generation: {gen_status}")
            logger.info(f"    Build: {build_status}")
            logger.info(f"    Test: {test_status}")
            if getattr(iter_log, 'error_message', None):
                logger.warning(f"    Error: {iter_log.error_message[:200]}")

        return session.success

    except Exception as e:
        logger.error(f"Spring Boot test failed: {str(e)}", exc_info=True)
        return False


def test_python_ml_pipeline():
    """Test 3: Python ML Pipeline Package generation."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Python ML Pipeline Package Generation")
    logger.info("="*80)

    requirements = """
    Create a Python ML package for data science workflows:
    - DataLoader class for loading CSV and preprocessing data
    - FeatureEngineering class with scaling, encoding, feature selection
    - ModelTrainer class using scikit-learn for training multiple algorithms
    - ModelEvaluator class for cross-validation, metrics calculation
    - Utility functions for train/test splitting and visualization
    - setup.py with proper metadata and dependencies
    - pyproject.toml with build configuration
    - requirements.txt with scikit-learn, pandas, numpy, matplotlib
    - Unit tests with pytest covering all modules
    - conftest.py with fixtures for test data
    - __init__.py files for proper package structure
    - README.md with usage examples
    Ensure proper imports between modules, no circular dependencies, 
    and all external dependencies are correctly specified.
    """

    orchestrator = OrchestratorAgent()

    try:
        start_time = time.time()

        session = orchestrator.generate_project(
            requirements=requirements.strip(),
            project_name="ml_pipeline",
            project_template="python_package",
            language=ProgrammingLanguage.PYTHON,
            max_iterations=3,
        )

        duration = time.time() - start_time

        # Check results
        logger.info(f"\nML Pipeline Package Generation Results:")
        logger.info(f"  Status: {'✅ SUCCESS' if session.success else '❌ FAILED'}")
        logger.info(f"  Iterations: {len(session.iterations)}")
        logger.info(f"  Files Generated: {len(session.files) if hasattr(session, 'files') else 0}")
        logger.info(f"  Dependencies: {len(session.all_dependencies) if hasattr(session, 'all_dependencies') else 0}")
        logger.info(f"  Duration: {duration:.2f}s")

        if session.files:
            logger.info(f"\n  Generated Files:")
            for file in session.files:
                logger.info(f"    - {file.filename} ({len(file.code)} bytes)")

        if session.all_dependencies:
            logger.info(f"\n  Dependencies:")
            for dep in session.all_dependencies:
                logger.info(f"    - {dep}")

        # Detailed iteration logs
        for i, iter_log in enumerate(session.iterations, 1):
            iteration_label = getattr(iter_log, 'iteration_number', i)
            logger.info(f"\n  Iteration {iteration_label}:")
            gen_status = getattr(iter_log, 'code_gen_status', getattr(iter_log, 'generation_status', 'UNKNOWN'))
            build_status = getattr(iter_log, 'build_status', 'UNKNOWN')
            test_status = getattr(iter_log, 'test_status', 'UNKNOWN')
            logger.info(f"    Generation: {gen_status}")
            logger.info(f"    Build: {build_status}")
            logger.info(f"    Test: {test_status}")
            if getattr(iter_log, 'error_message', None):
                logger.warning(f"    Error: {iter_log.error_message[:200]}")

        return session.success

    except Exception as e:
        logger.error(f"ML Pipeline test failed: {str(e)}", exc_info=True)
        return False


def print_summary(results):
    """Print test summary."""
    logger.info("\n" + "="*80)
    logger.info("INTEGRATION TEST SUMMARY")
    logger.info("="*80)

    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed

    logger.info(f"\nTotal Tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")

    logger.info(f"\nDetailed Results:")
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        logger.info(f"  {test_name}: {status}")

    logger.info("\n" + "="*80)

    return failed == 0


if __name__ == "__main__":
    logger.info("Starting Phase 3 Integration Tests")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    results = {
        "FastAPI TODO API": test_fastapi_todo_api(),
        "Spring Boot Auth Microservice": test_spring_boot_auth(),
        "Python ML Pipeline": test_python_ml_pipeline(),
    }

    all_passed = print_summary(results)

    sys.exit(0 if all_passed else 1)
