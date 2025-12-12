"""Test script to verify log handler functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.streamlit_log_handler import get_streamlit_log_handler
from src.utils.logger import (
    orchestrator_logger,
    code_gen_logger,
    build_logger,
    attach_streamlit_handler
)

def test_log_handler():
    """Test log handler capture."""
    print("=" * 60)
    print("Testing Streamlit Log Handler")
    print("=" * 60)
    
    # Get handler
    handler = get_streamlit_log_handler()
    print(f"\n✓ Log handler created: {handler}")
    
    # Attach to loggers
    attach_streamlit_handler()
    print("✓ Handler attached to all loggers")
    
    # Generate some logs
    print("\n--- Generating test logs ---")
    orchestrator_logger.info("Test log from orchestrator")
    code_gen_logger.info("Test log from code generator")
    build_logger.warning("Test warning from build agent")
    
    # Retrieve logs
    print("\n--- Captured logs ---")
    logs = handler.get_logs()
    print(f"Total logs captured: {len(logs)}")
    
    for log in logs:
        print(f"  [{log['level']}] {log['message']}")
    
    # Test formatted output
    print("\n--- Formatted logs ---")
    formatted = handler.get_formatted_logs()
    print(formatted)
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_log_handler()
