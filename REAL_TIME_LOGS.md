# Real-Time Log Display - Implementation Guide

## Overview
Implemented a **Streamlit-native real-time log streaming solution** that displays all agent execution logs in the UI without requiring Socket.IO or external servers.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (Port 8501)                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────────────────────────────────────┐     │
│  │  Progress Section                                 │     │
│  │  ├─ Progress Bar                                  │     │
│  │  ├─ Status Text                                   │     │
│  │  └─ 📋 Execution Logs (Expandable)               │     │
│  │     ├─ [🔄 Refresh] [🗑️ Clear Logs]             │     │
│  │     └─ Log Display (400px scrollable)            │     │
│  └───────────────────────────────────────────────────┘     │
│                          ▲                                   │
│                          │ Updates via progress_callback    │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│           StreamlitLogHandler (Thread-Safe)                 │
├──────────────────────────┼──────────────────────────────────┤
│  deque(maxlen=200)       │ Captures all logs in memory     │
│  ├─ {timestamp, level, message, name}                      │
│  ├─ get_logs(n)          │ Retrieve last n logs            │
│  ├─ get_formatted_logs() │ Format as string                │
│  └─ clear_logs()         │ Clear all logs                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           │ Attached to all loggers
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Loggers                            │
├─────────────────────────────────────────────────────────────┤
│  ├─ orchestrator_logger                                     │
│  ├─ code_gen_logger                                         │
│  ├─ build_logger                                            │
│  ├─ test_logger                                             │
│  └─ ui_logger                                               │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. StreamlitLogHandler (`src/utils/streamlit_log_handler.py`)
**Purpose:** Thread-safe log capture for UI display

**Features:**
- Stores up to 200 logs in memory (configurable)
- Thread-safe using `threading.Lock`
- Provides formatted log retrieval
- Can be enabled/disabled on demand

**Key Methods:**
```python
handler = get_streamlit_log_handler()
logs = handler.get_logs(n=50)  # Last 50 logs
formatted = handler.get_formatted_logs(n=100)  # As string
handler.clear_logs()  # Clear all
```

### 2. Logger Updates (`src/utils/logger.py`)
**Added:**
```python
def attach_streamlit_handler():
    """Attach Streamlit log handler to all loggers."""
```

Called during UI initialization to enable log capture.

### 3. UI Integration (`src/ui/streamlit_app.py`)

**Session State Initialization:**
```python
st.session_state.log_handler = get_streamlit_log_handler()
attach_streamlit_handler()
```

**Progress Section Enhancement:**
```python
with st.expander("📋 Execution Logs", expanded=True):
    # Controls
    col1, col2, col3 = st.columns([1, 1, 3])
    [🔄 Refresh] [🗑️ Clear Logs]
    
    # Log display (auto-updates)
    log_container.code(logs, language="log", height=400)
```

**Callback Enhancement:**
```python
def progress_callback(message: str, iteration: int):
    # Update progress bar & status
    ...
    
    # Update logs in real-time
    logs = st.session_state.log_handler.get_formatted_logs(100)
    st.session_state.log_container.code(logs, language="log")
```

### 4. Orchestrator Updates (`src/agents/orchestrator.py`)
**Added checkpoint callbacks:**
- ✓ After code generation
- ✓ After build completion
- ✓ After testing

This ensures UI updates at key milestones.

## How It Works

### Execution Flow:

1. **User clicks "Generate Code"**
   ```
   UI → Initialize log handler → Clear previous logs
   ```

2. **Orchestrator starts iteration**
   ```
   Orchestrator → logger.info("Step 1: Code Generation")
                ↓
   StreamlitLogHandler → Captures log in deque
                ↓
   progress_callback() → Reads logs from handler
                ↓
   UI → Displays in code block (auto-scrolling)
   ```

3. **Each agent logs its actions**
   ```
   CodeGenerator: "Generating Python code..."
   BuildAgent:    "Installing dependencies: requests, pandas"
   BuildAgent:    "✓ Syntax valid"
   TestingAgent:  "Executing code..."
   TestingAgent:  "✅ All tests passed!"
   ```

4. **UI updates in real-time**
   - Progress bar moves forward
   - Status text changes
   - **Logs appear instantly** in the expander

### Log Format:
```
12:34:56 | orchestrator | INFO | === Iteration 1/3 ===
12:34:57 | code_generator | INFO | Generating Python code for requirements
12:34:58 | build_agent | INFO | Installing Python dependencies: requests
12:34:59 | build_agent | INFO | ✓ Syntax valid: generated_code.py
12:35:00 | testing_agent | INFO | Executing code...
12:35:01 | orchestrator | INFO | ✅ All tests passed!
```

## Usage

### For Users:
1. Start code generation
2. **Expand "📋 Execution Logs"** to see real-time progress
3. Watch as agents log their actions
4. Use **🔄 Refresh** to manually update (auto-updates via callbacks)
5. Use **🗑️ Clear Logs** to reset before new generation

### For Developers:
Add logs anywhere in agents:
```python
from src.utils.logger import build_logger as logger

logger.info("Starting Maven compilation...")
logger.warning("Build failed, retrying...")
logger.error("Critical error occurred")
```

Logs automatically appear in UI!

## Benefits

✅ **No External Dependencies** - Pure Streamlit + Python logging  
✅ **Thread-Safe** - Works with concurrent operations  
✅ **Memory Efficient** - Automatic log rotation (max 200)  
✅ **Real-Time Updates** - Appears as agents work  
✅ **User Control** - Clear/refresh buttons  
✅ **Developer Friendly** - Just use existing loggers  
✅ **Debugging Aid** - See exactly what agents are doing  
✅ **Professional UX** - Syntax-highlighted code display  

## Comparison with Socket.IO

| Feature | Streamlit Native | Socket.IO |
|---------|-----------------|-----------|
| Setup | ✅ Simple | ❌ Complex (2 servers) |
| Dependencies | ✅ None | ❌ flask-socketio, python-socketio |
| Real-time | ✅ Yes (via callbacks) | ✅ Yes (true push) |
| Multi-client | ❌ No (single session) | ✅ Yes |
| Performance | ✅ Fast | ✅ Fast |
| Maintenance | ✅ Easy | ❌ Moderate |

## Future Enhancements

1. **Log Filtering**
   - Filter by log level (INFO/WARNING/ERROR)
   - Filter by agent name
   - Search in logs

2. **Download Logs**
   - Export logs as .txt file
   - Download full session logs

3. **Log Statistics**
   - Show error count
   - Show warning count
   - Time spent per agent

4. **Auto-scroll Control**
   - Toggle auto-scroll to bottom
   - Preserve scroll position

5. **Color Coding**
   - Red for errors
   - Yellow for warnings
   - Green for success messages

## Testing

**Start Streamlit:**
```bash
python -m streamlit run src/ui/streamlit_app.py
```

**Generate code and observe:**
1. Logs appear in real-time as generation progresses
2. Each agent's actions are visible
3. Build/test output shows immediately
4. Can clear logs between runs

**Expected Output:**
- Iteration start/end markers
- Code generation messages
- Dependency installation logs
- Build compilation output
- Test execution results
- Success/failure summaries

## Troubleshooting

**Logs not appearing:**
- Check `attach_streamlit_handler()` is called in `initialize_session_state()`
- Verify log handler is in session state: `st.session_state.log_handler`

**Logs not updating:**
- Ensure `progress_callback()` is being called
- Check `log_container` exists in session state

**UI freezing:**
- Streamlit reruns entire script - this is normal
- Progress section only shown when `generation_in_progress=True`

## Summary

You now have a **professional real-time log display** that:
- Shows all agent activity instantly
- Requires no external services
- Is simple to maintain
- Provides excellent debugging visibility

All agent logs are captured and displayed beautifully in the UI! 🎉
