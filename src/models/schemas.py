"""Pydantic models for data validation and state management."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProgrammingLanguage(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVA = "java"


class AgentStatus(str, Enum):
    """Agent execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ErrorType(str, Enum):
    """Types of errors that can occur."""

    SYNTAX = "syntax"
    BUILD = "build"
    RUNTIME = "runtime"
    LOGIC = "logic"
    MISSING_CREDENTIALS = "missing_credentials"


class TestCase(BaseModel):
    """Individual test case result."""

    name: str
    status: str
    description: str
    error: Optional[str] = None


class PerformanceMetrics(BaseModel):
    """Code execution performance metrics."""

    execution_time_seconds: float
    memory_used_mb: Optional[float] = None


class BuildResult(BaseModel):
    """Build agent output."""

    status: str
    dependencies: List[str] = Field(default_factory=list)
    build_instructions: str = ""
    errors: List[str] = Field(default_factory=list)
    suggested_fixes: List[str] = Field(default_factory=list)


class TestResult(BaseModel):
    """Testing agent output."""

    status: str
    test_cases: List[TestCase] = Field(default_factory=list)
    execution_logs: str = ""
    performance: Optional[PerformanceMetrics] = None
    issues_found: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class CodeArtifact(BaseModel):
    """Generated code artifact."""

    language: ProgrammingLanguage
    code: str
    filename: str
    dependencies: List[str] = Field(default_factory=list)


class FileArtifact(BaseModel):
    """Single file in a multi-file project."""

    filename: str  # e.g., "src/main.py", "src/Main.java"
    code: str
    language: str
    size: int = 0
    filepath: Optional[str] = None  # Full path relative to project root


class IterationLog(BaseModel):
    """Log entry for a single iteration."""

    iteration_number: int
    timestamp: datetime = Field(default_factory=datetime.now)

    # Agent statuses
    code_gen_status: AgentStatus = AgentStatus.PENDING
    build_status: AgentStatus = AgentStatus.PENDING
    test_status: AgentStatus = AgentStatus.PENDING

    # Artifacts
    generated_code: Optional[str] = None
    build_result: Optional[BuildResult] = None
    test_result: Optional[TestResult] = None

    # Error tracking
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None
    error_context: Optional[str] = None


class GenerationSession(BaseModel):
    """Complete code generation session."""

    session_id: str
    requirements: str
    language: ProgrammingLanguage
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Session state
    status: AgentStatus = AgentStatus.PENDING
    current_iteration: int = 0
    max_iterations: int = 5

    # Results
    iterations: List[IterationLog] = Field(default_factory=list)
    final_code: Optional[CodeArtifact] = None

    # Runtime data
    runtime_credentials: Dict[str, Any] = Field(default_factory=dict)
    missing_credentials: List[str] = Field(default_factory=list)

    # Metadata
    total_execution_time: float = 0.0
    success: bool = False

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CodeGenerationRequest(BaseModel):
    """Request model for code generation."""

    requirements: str = Field(..., min_length=10)
    language: ProgrammingLanguage
    max_iterations: int = Field(default=5, ge=1, le=10)
    runtime_credentials: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Generic agent response."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ProjectSession(GenerationSession):
    """Extended session for multi-file projects."""

    project_template: str = ""  # e.g., "fastapi", "spring_boot"
    project_name: str = ""
    files: List[FileArtifact] = Field(default_factory=list)  # All generated files
    file_tree: Dict[str, Any] = Field(default_factory=dict)  # Directory structure
    root_dir: str = ""  # outputs/sessions/<id>/
    has_dockerfile: bool = False
    has_ci_config: bool = False
    all_dependencies: List[str] = Field(default_factory=list)  # Merged from all files
