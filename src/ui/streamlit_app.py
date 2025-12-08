"""Streamlit UI for Agentic Code Studio."""

import sys
import os

# Add the root directory to sys.path so that Python can find 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import io
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.agents.orchestrator import OrchestratorAgent
from src.config.settings import settings
from src.models.schemas import AgentStatus, ProgrammingLanguage
from src.utils.logger import ui_logger as logger

# Page configuration
st.set_page_config(
    page_title="Agentic Code Studio",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .status-success {
        color: #00c853;
        font-weight: bold;
    }
    .status-running {
        color: #ff9800;
        font-weight: bold;
    }
    .status-failed {
        color: #f44336;
        font-weight: bold;
    }
    .iteration-box {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


def initialize_session_state():
    """Initialize Streamlit session state."""
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = OrchestratorAgent()

    if "current_session" not in st.session_state:
        st.session_state.current_session = None

    if "current_project_session" not in st.session_state:
        st.session_state.current_project_session = None

    if "runtime_credentials" not in st.session_state:
        st.session_state.runtime_credentials = {}

    if "generation_in_progress" not in st.session_state:
        st.session_state.generation_in_progress = False

    if "generation_mode" not in st.session_state:
        st.session_state.generation_mode = "single_file"


def render_header():
    """Render application header."""
    st.markdown('<h1 class="main-header">🤖 Agentic Code Studio</h1>', unsafe_allow_html=True)
    st.markdown("**Multi-Agent AI System for Autonomous Code Generation**")
    st.markdown("---")


def render_main_interface():
    """Render the main code generation interface."""
    st.subheader("📝 Code Generation Request")

    col1, col2 = st.columns([2, 1])

    with col1:
        requirements = st.text_area(
            "Describe what code you want to generate:",
            height=150,
            placeholder="Example: Write a Python script for inserting 100 customer data in PostgreSQL from a CSV and populate age groups based on ranges...",
            key="requirements_input",
        )

    with col2:
        language = st.selectbox(
            "Programming Language",
            options=[lang.value for lang in ProgrammingLanguage],
            format_func=lambda x: x.upper(),
            key="language_select",
        )

        max_iterations = st.number_input(
            "Max Iterations",
            min_value=1,
            max_value=10,
            value=settings.max_iterations,
            key="max_iterations_input",
        )

        st.markdown("---")
        generate_button = st.button(
            "🚀 Generate Code",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.generation_in_progress,
        )

    # Runtime credentials section
    with st.expander("⚙️ Runtime Credentials (Optional)", expanded=False):
        st.info("Provide API keys or credentials that generated code might need.")

        cred_key = st.text_input("Credential Name (e.g., API_KEY)", key="cred_key_input")
        cred_value = st.text_input("Credential Value", type="password", key="cred_value_input")

        col_add, col_clear = st.columns(2)
        with col_add:
            if st.button("➕ Add Credential"):
                if cred_key and cred_value:
                    st.session_state.runtime_credentials[cred_key] = cred_value
                    st.success(f"Added: {cred_key}")
                    st.rerun()

        with col_clear:
            if st.button("🗑️ Clear All"):
                st.session_state.runtime_credentials = {}
                st.rerun()

        if st.session_state.runtime_credentials:
            st.write("**Current Credentials:**")
            for key in st.session_state.runtime_credentials.keys():
                st.text(f"✓ {key}")

    # Database configuration
    with st.expander("🗄️ Database Configuration", expanded=False):
        st.info("Configure PostgreSQL connection for generated code.")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Host", value=settings.db_host, disabled=True)
            st.text_input("Database", value=settings.db_name, disabled=True)
        with col2:
            st.text_input("Port", value=str(settings.db_port), disabled=True)
            st.text_input("User", value=settings.db_user, disabled=True)

        st.caption("💡 Make sure PostgreSQL is running locally with these settings")

    return generate_button, requirements, language, max_iterations


def render_project_interface():
    """Render the project generation interface."""
    from src.config.project_templates import list_templates

    st.subheader("🏗️ Multi-File Project Generation")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        requirements = st.text_area(
            "Describe what project you want to generate:",
            height=150,
            placeholder="Example: Create a FastAPI REST API for a TODO application with user authentication, database models, CRUD endpoints, and Docker support...",
            key="project_requirements_input",
        )

    with col2:
        project_name = st.text_input(
            "Project Name",
            value="my_project",
            placeholder="my_awesome_project",
            key="project_name_input",
        )

        templates = list_templates()
        # Create a mapping from display name to template key
        template_name_to_key = {t["name"]: t["key"] for t in templates}
        template_options = [t["name"] for t in templates]
        selected_template_name = st.selectbox(
            "Project Template",
            options=template_options,
            key="template_select",
        )
        # Map the selected display name back to the template key
        template_name = template_name_to_key.get(selected_template_name, selected_template_name)

    with col3:
        language = st.selectbox(
            "Programming Language",
            options=[lang.value for lang in ProgrammingLanguage],
            format_func=lambda x: x.upper(),
            key="project_language_select",
        )

        max_iterations = st.number_input(
            "Max Iterations",
            min_value=1,
            max_value=10,
            value=settings.max_iterations,
            key="project_max_iterations_input",
        )

        st.markdown("---")
        generate_project_button = st.button(
            "🚀 Generate Project",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.generation_in_progress,
        )

    return generate_project_button, requirements, project_name, template_name, language, max_iterations


def render_progress_section():
    """Render real-time progress updates."""
    if not st.session_state.generation_in_progress:
        return

    st.markdown("---")
    st.subheader("⚡ Generation Progress")

    progress_container = st.container()

    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Store in session state for callback access
        st.session_state.progress_bar = progress_bar
        st.session_state.status_text = status_text


def progress_callback(message: str, iteration: int):
    """Callback function for progress updates."""
    if hasattr(st.session_state, "progress_bar") and hasattr(st.session_state, "status_text"):
        max_iter = st.session_state.get("max_iterations_input", settings.max_iterations)
        progress = iteration / max_iter
        st.session_state.progress_bar.progress(progress)
        st.session_state.status_text.text(message)


def render_results_section(session):
    """Render code generation results."""
    st.markdown("---")
    st.subheader("📊 Results")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status_class = "status-success" if session.success else "status-failed"
        st.markdown(
            f'<p class="{status_class}">{"✅ SUCCESS" if session.success else "❌ FAILED"}</p>',
            unsafe_allow_html=True,
        )

    with col2:
        st.metric("Iterations", f"{session.current_iteration}/{session.max_iterations}")

    with col3:
        st.metric("Execution Time", f"{session.total_execution_time:.2f}s")

    with col4:
        st.metric("Language", session.language.value.upper())

    # Missing credentials warning
    if session.missing_credentials:
        st.warning(f"⚠️ Missing credentials detected: {', '.join(session.missing_credentials)}")
        st.info("Add them in the Runtime Credentials section and try again.")

    # Final code display
    if session.final_code:
        st.success("✨ Generated Code:")
        st.code(session.final_code.code, language=session.language.value)

        # Download options
        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                label="📥 Download Code",
                data=session.final_code.code,
                file_name=session.final_code.filename,
                mime="text/plain",
            )

        with col2:
            # Create ZIP with code and dependencies
            zip_buffer = create_project_zip(session)
            st.download_button(
                label="📦 Download Project ZIP",
                data=zip_buffer,
                file_name=f"generated_project_{session.session_id}.zip",
                mime="application/zip",
            )

        # Dependencies
        if session.final_code.dependencies:
            st.info(f"**Dependencies:** {', '.join(session.final_code.dependencies)}")

    # Iteration logs
    with st.expander("📜 Iteration Logs", expanded=False):
        for iter_log in session.iterations:
            render_iteration_log(iter_log)


def render_iteration_log(iter_log):
    """Render details of a single iteration."""
    st.markdown(f"### Iteration {iter_log.iteration_number}")

    col1, col2, col3 = st.columns(3)

    with col1:
        status = get_status_emoji(iter_log.code_gen_status)
        st.write(f"**Code Gen:** {status}")

    with col2:
        status = get_status_emoji(iter_log.build_status)
        st.write(f"**Build:** {status}")

    with col3:
        status = get_status_emoji(iter_log.test_status)
        st.write(f"**Testing:** {status}")

    if iter_log.error_message:
        st.error(f"**Error:** {iter_log.error_message}")

    if iter_log.generated_code:
        with st.expander("View Generated Code"):
            st.code(iter_log.generated_code, language="python")

    if iter_log.build_result and iter_log.build_result.errors:
        with st.expander("Build Errors"):
            for error in iter_log.build_result.errors:
                st.text(error)

    if iter_log.test_result:
        with st.expander("Test Results"):
            for test_case in iter_log.test_result.test_cases:
                status_icon = "✅" if test_case.status == "pass" else "❌"
                st.write(f"{status_icon} **{test_case.name}**: {test_case.description}")
                if test_case.error:
                    st.error(test_case.error)

    st.markdown("---")


def get_status_emoji(status: AgentStatus) -> str:
    """Get emoji for agent status."""
    emoji_map = {
        AgentStatus.SUCCESS: "✅ Success",
        AgentStatus.FAILED: "❌ Failed",
        AgentStatus.RUNNING: "🔄 Running",
        AgentStatus.PENDING: "⏳ Pending",
        AgentStatus.SKIPPED: "⏭️ Skipped",
    }
    return emoji_map.get(status, "❓ Unknown")


def create_project_zip(session) -> bytes:
    """Create a ZIP file with all project files."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Add all project files
        if hasattr(session, "files") and session.files:
            for file in session.files:
                zip_file.writestr(file.filename, file.code)

        # Add README
        readme_content = f"""# {session.project_name}

## Description
{session.requirements}

## Project Details
- **Template:** {session.project_template}
- **Language:** {session.language.value.upper()}
- **Session ID:** {session.session_id}
- **Generated:** {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}

## Files
{len(session.files) if hasattr(session, 'files') else 0} files generated

## Dependencies
{', '.join(session.all_dependencies) if hasattr(session, 'all_dependencies') and session.all_dependencies else 'None'}

## Getting Started

### Installation
```bash
cd {session.project_name}
pip install -r requirements.txt  # For Python
# or
mvn clean install  # For Java
```

### Running
Check individual README files in the project structure for specific instructions.
"""
        zip_file.writestr("README.md", readme_content)

        # Add requirements.txt for Python projects
        if session.language == ProgrammingLanguage.PYTHON and hasattr(session, "all_dependencies") and session.all_dependencies:
            requirements_txt = "\n".join(session.all_dependencies)
            zip_file.writestr("requirements.txt", requirements_txt)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def render_project_results_section(session):
    """Render project generation results."""
    st.markdown("---")
    st.subheader("📊 Project Generation Results")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Status", "✅ Success" if session.success else "❌ Failed")

    with col2:
        st.metric("Iterations", len(session.iterations))

    with col3:
        st.metric("Files Generated", len(session.files) if hasattr(session, "files") else 0)

    with col4:
        duration = session.total_execution_time or 0
        st.metric("Time (s)", f"{duration:.2f}")

    # Project summary
    st.info(
        f"""
        **Project:** {session.project_name}
        **Template:** {session.project_template}
        **Language:** {session.language.value.upper()}
        """
    )

    # Generated files
    if hasattr(session, "files") and session.files:
        with st.expander("📁 Generated Files", expanded=True):
            for file in session.files:
                with st.expander(f"📄 {file.filename} ({file.language})"):
                    st.code(file.code[:500] + "..." if len(file.code) > 500 else file.code, language=file.language)

    # Dependencies
    if hasattr(session, "all_dependencies") and session.all_dependencies:
        st.info(f"**Dependencies:** {', '.join(session.all_dependencies)}")

    # Download project
    st.markdown("---")
    project_zip = create_project_zip(session)
    st.download_button(
        label=f"⬇️ Download {session.project_name}.zip",
        data=project_zip,
        file_name=f"{session.project_name}_{session.session_id}.zip",
        mime="application/zip",
    )

    # Iteration logs
    with st.expander("📜 Iteration Logs", expanded=False):
        for iter_log in session.iterations:
            render_iteration_log(iter_log)


def render_history_sidebar():
    """Render session history in sidebar."""
    st.sidebar.title("📚 Session History")

    sessions = st.session_state.orchestrator.list_sessions()

    if not sessions:
        st.sidebar.info("No previous sessions found")
        return

    for session_info in sessions[:10]:  # Show last 10
        with st.sidebar.expander(f"📄 {session_info['session_id']}", expanded=False):
            st.write(f"**Language:** {session_info['language'].upper()}")
            st.write(f"**Status:** {'✅' if session_info['success'] else '❌'}")
            st.write(f"**Created:** {session_info['created_at'].strftime('%Y-%m-%d %H:%M')}")
            st.caption(f"*{session_info['requirements'][:80]}...*")

            if st.button(f"Load", key=f"load_{session_info['session_id']}"):
                loaded_session = st.session_state.orchestrator.load_session(
                    session_info["session_id"]
                )
                if loaded_session:
                    st.session_state.current_session = loaded_session
                    st.rerun()


def render_settings_sidebar():
    """Render application settings in sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.title("⚙️ Settings")

    st.sidebar.write(f"**Max Iterations:** {settings.max_iterations}")
    st.sidebar.write(f"**Execution Timeout:** {settings.execution_timeout}s")
    st.sidebar.write(f"**Max Memory:** {settings.max_memory_mb}MB")
    st.sidebar.write(
        f"**Session Persistence:** {'✅' if settings.enable_session_persistence else '❌'}"
    )


def main():
    """Main application entry point."""
    initialize_session_state()
    render_header()

    # Mode selector
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Single File Generation", use_container_width=True):
            st.session_state.generation_mode = "single_file"
            st.rerun()

    with col2:
        if st.button("🏗️ Multi-File Project", use_container_width=True):
            st.session_state.generation_mode = "project"
            st.rerun()

    st.markdown("---")

    # Single file mode
    if st.session_state.generation_mode == "single_file":
        generate_button, requirements, language, max_iterations = render_main_interface()

        # Handle code generation
        if generate_button:
            if not requirements or len(requirements.strip()) < 10:
                st.error("Please provide detailed requirements (at least 10 characters)")
            else:
                st.session_state.generation_in_progress = True
                st.rerun()

        # Progress section
        if st.session_state.generation_in_progress:
            render_progress_section()

            # Execute generation
            try:
                lang_enum = ProgrammingLanguage(language)

                session = st.session_state.orchestrator.generate_code(
                    requirements=requirements,
                    language=lang_enum,
                    max_iterations=max_iterations,
                    runtime_credentials=st.session_state.runtime_credentials,
                    progress_callback=progress_callback,
                )

                st.session_state.current_session = session
                st.session_state.generation_in_progress = False

                st.rerun()

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                logger.error(f"Generation error: {str(e)}", exc_info=True)
                st.session_state.generation_in_progress = False

        # Display results if available
        if st.session_state.current_session and not st.session_state.generation_in_progress:
            render_results_section(st.session_state.current_session)

    # Project mode
    else:
        generate_button, requirements, project_name, template_name, language, max_iterations = render_project_interface()

        # Handle project generation
        if generate_button:
            if not requirements or len(requirements.strip()) < 10:
                st.error("Please provide detailed requirements (at least 10 characters)")
            elif not project_name:
                st.error("Please enter a project name")
            else:
                st.session_state.generation_in_progress = True
                st.rerun()

        # Progress section
        if st.session_state.generation_in_progress:
            render_progress_section()

            # Execute project generation
            try:
                lang_enum = ProgrammingLanguage(language)

                session = st.session_state.orchestrator.generate_project(
                    requirements=requirements,
                    project_name=project_name,
                    project_template=template_name,
                    language=lang_enum,
                    max_iterations=max_iterations,
                    runtime_credentials=st.session_state.runtime_credentials,
                    progress_callback=progress_callback,
                )

                st.session_state.current_project_session = session
                st.session_state.generation_in_progress = False

                st.rerun()

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                logger.error(f"Project generation error: {str(e)}", exc_info=True)
                st.session_state.generation_in_progress = False

        # Display project results if available
        if st.session_state.current_project_session and not st.session_state.generation_in_progress:
            render_project_results_section(st.session_state.current_project_session)

    # Sidebar
    render_history_sidebar()
    render_settings_sidebar()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("🤖 Powered by Google Gemini & LangChain")


if __name__ == "__main__":
    main()
