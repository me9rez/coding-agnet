# Development Guide

## Python Layer

### Dependencies

The agent uses `agent-framework` (Microsoft Agent Framework) as its LLM client layer.
The core and openai packages are installed as editable from the local clone:

```bash
cd python
uv venv
uv pip install -e "../../agent-framework/python/packages/core" --no-deps
uv pip install -e "../../agent-framework/python/packages/openai" --no-deps
uv pip install pydantic httpx openai python-dotenv
```

### Running

```bash
# CLI test mode — prints events to stderr
.venv/Scripts/python -m coding_agent.main --test "Your prompt here"

# CLI test with custom model
.venv/Scripts/python -m coding_agent.main --test "Hello" --model deepseek-chat --base-url https://api.deepseek.com/v1

# Gateway mode — for TUI connection
.venv/Scripts/python -m coding_agent.main
```

### Adding a new tool

1. Create an async function in `tools/coding_tools.py`
2. Register it in `create_coding_tools()` as a `FunctionTool` instance
3. The tool's parameter names and docstring are automatically converted to JSON schema

Example:
```python
async def _my_tool(param1: str, param2: int = 42) -> str:
    """Description of what this tool does."""
    return f"Result: {param1}, {param2}"

# In create_coding_tools():
FunctionTool(name="my_tool", description="Description...", func=_my_tool),
```

## TUI Layer

### Dependencies

The TUI uses `@simon_he/vue-tui` for terminal rendering and `tsdown` for building.

```bash
cd tui
npm install
```

### Development workflow

```bash
# Type check
npm run type-check

# Build
npm run build      # tsdown

# Dev (build + run)
npm run dev        # builds then executes
```

### Architecture

The TUI is a single-page terminal app with:

- **main.ts**: entry point — creates the terminal app, stdout renderer, stdin driver
- **app.ts**: render function component — builds the UI tree using `h()` calls
- **gatewayClient.ts**: manages the Python subprocess — spawns, reads stdout, writes stdin
- **gatewayTypes.ts**: TypeScript type definitions for all gateway events

### Component hierarchy

```
createTerminalApp() → mounts App component
  └── App (render function)
      ├── Title bar (TText)
      ├── Separator (TText)
      ├── Message list (TBox per message)
      │   ├── User text (TBox + TText)
      │   ├── Assistant text (TBox + TText)
      │   ├── Thinking block (TBox + TText, collapsible)
      │   ├── Tool execution (TBox + TText, collapsible)
      │   └── Error (TBox + TText)
      ├── Streaming area (TBox + TText)
      ├── Status indicator (TText)
      ├── Token bar (TText)
      └── Input line (TBox + TText)
```

### Event flow

```
GatewayEvent → handleEvent() → transcript[] / streaming / token count
                              → render() → VNode tree → terminal output
```

## Testing

### Python unit test

```python
import asyncio
from agent_framework._types import Message
from coding_agent.tools.coding_tools import create_coding_tools
from coding_agent.loop import run_coding_agent

# Use the fake client (no API key needed)
from coding_agent.main import _FakeClient

async def test():
    client = _FakeClient()
    messages = [Message(role="user", contents=["Hello"])]
    tools = create_coding_tools()
    events = []
    await run_coding_agent(client, messages, tools, on_event=events.append)
    print(f"Generated {len(events)} events")

asyncio.run(test())
```

### Full integration test

Requires `DEEPSEEK_API_KEY` env var:

```bash
cd python
.venv/Scripts/python -m coding_agent.main --test "Run echo hello"
```

## Common Issues

### "No module named 'coding_agent'"

Ensure `PYTHONPATH` includes `python/src`, or run from the `python/` directory.

### TUI shows "Cannot find module"

Run `npm install` first, then `npm run build`.

### Python subprocess "module not found"

The TUI sets `PYTHONPATH` automatically in `gatewayClient.ts`. If paths differ, update the `pythonSrc` variable.

### Type errors after dependency update

The tsconfig has strict settings. Run `npx tsc --noEmit` and fix any reported issues.
