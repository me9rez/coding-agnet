# Coding Agent

A lightweight coding agent with fine-grained event streaming, JSON-RPC gateway, and Vue TUI terminal interface.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Python layer                                                │
│                                                              │
│  ┌─────────────────────┐   ┌─────────────────────────────┐   │
│  │ Agent Loop          │   │ Tools                       │   │
│  │ run_coding_agent()  │──▶│ bash, read, write,          │   │
│  │ custom loop with    │   │ edit, search, list_dir,     │   │
│  │ fine-grained events │   │ load_skill                  │   │
│  └─────────┬───────────┘   └─────────────────────────────┘   │
│            │                                                  │
│            ▼                                                  │
│  ┌─────────────────────────────────────┐                      │
│  │ Gateway (stdio JSON-RPC)            │                      │
│  │ stdin: {"method":"prompt",...}      │                      │
│  │ stdout: {"type":"text_delta",...}   │                      │
│  └──────────────────┬──────────────────┘                      │
│                     │ spawn subprocess                        │
├─────────────────────┼────────────────────────────────────────┤
│ TypeScript layer    │                                         │
│                     ▼                                         │
│  ┌─────────────────────────────────────┐                      │
│  │ GatewayClient                       │                      │
│  │ gatewayClient.ts — spawns Python    │                      │
│  │ reads stdout events, sends stdin    │                      │
│  └──────────────────┬──────────────────┘                      │
│                     │                                          │
│                     ▼                                          │
│  ┌─────────────────────────────────────┐                      │
│  │ Vue TUI (@simon_he/vue-tui)        │                      │
│  │ app.ts — render function component  │                      │
│  │ Main entry: main.ts (createTerminal)│                      │
│  └─────────────────────────────────────┘                      │
└──────────────────────────────────────────────────────────────┘
```

**Key design decisions:**

- **Custom agent loop** (not `create_harness_agent`): emits per-chunk `thinking_delta`, `text_delta`, tool lifecycle events that `AgentResponseUpdate` cannot express.
- **Gateway pattern**: Python subprocess communicates with TypeScript TUI over stdio JSON-RPC, following Hermes's `tui_gateway` design.
- **Vue TUI**: `@simon_he/vue-tui` provides terminal rendering with support for browser DOM and real terminals.

## Features

| Feature | Status |
|---------|--------|
| LLM provider: DeepSeek / OpenAI chat completions | ✅ |
| Event streaming: text, thinking, tool call lifecycle | ✅ |
| Tool: bash shell execution | ✅ |
| Tool: file read / write / edit (exact replacement) | ✅ |
| Tool: file search (recursive regex) | ✅ |
| Tool: directory listing | ✅ |
| Tool: skill loading | ✅ |
| System prompt assembly | ✅ |
| Project context discovery | ✅ |
| Session persistence (JSONL) | ✅ |
| Skills system (SKILL.md) | ✅ |
| Context window compaction | ✅ |
| Thinking level control (off/low/medium/high) | ✅ |
| TUI: message collapsing (thinking/tool) | ✅ |
| TUI: token usage bar | ✅ |
| Multi-provider configuration | 🔲 |
| Session branching | 🔲 |

## Project Structure

```
coding-agent/
├── docs/
│   ├── proposal.md         # Original technical proposal
│   └── protocol.md         # Gateway JSON-RPC protocol spec
├── python/
│   ├── pyproject.toml
│   └── src/coding_agent/
│       ├── events.py         # 8 fine-grained event types
│       ├── system_prompt.py  # System prompt builder + project context
│       ├── session.py        # JSONL session persistence
│       ├── skills.py         # SKILL.md scanning + progressive loading
│       ├── compaction.py     # Context window compaction
│       ├── thinking.py       # Thinking level → provider params
│       ├── gateway/
│       │   ├── server.py     # stdio JSON-RPC dispatcher
│       │   ├── ws_server.py   # WebSocket gateway server
│       │   └── transport.py  # StdioTransport
└── tui/
    ├── package.json
    ├── tsconfig.json
    ├── tsdown.config.ts
    └── src/
        ├── main.ts           # Terminal app entry
        ├── app.ts            # Vue render function component
        ├── gatewayClient.ts  # Python subprocess manager
        ├── gatewayTypes.ts   # Event type definitions
        └── components/
            └── message-list.vue  # Legacy Vue SFC (for reference)
```

## Quick Start

### Prerequisites

- Python 3.14+
- Node.js 22+
- pnpm
- DeepSeek API key (or OpenAI-compatible)

### Setup

```bash
# Python — dependencies are in pyproject.toml
cd python
uv sync

# TUI
cd ../tui
pnpm install
```

### Configuration

All settings live in ``~/.coding-agent/settings.json``:

```json
{
  "model": "deepseek-v4-flash",
  "base_url": "https://api.deepseek.com/v1",
  "api_key": "sk-xxx",
  "thinking_level": "medium",
  "max_context_tokens": 1000000,
  "max_output_tokens": 384000,
  "keep_recent_tokens": 600000,
  "max_turns": 25
}
```

User-level skills go in ``~/.coding-agent/skills/``, project skills in ``skills/``.

### Run

```bash
# CLI test mode (standalone, no gateway needed)
cd python
uv run python -m coding_agent --test "List Python files"

# Terminal 1: Start the Python WebSocket gateway
cd python
uv run python -m coding_agent --ws-port 8765

# Terminal 2: Start the TUI (connects to ws://127.0.0.1:8765)
cd ../tui
pnpm dev
```
## Event Reference

The agent loop emits these fine-grained events:

| Event | Payload | Description |
|-------|---------|-------------|
| `thinking_delta` | `{delta}` | Reasoning token (Anthropic) |
| `text_delta` | `{delta}` | Visible text token |
| `tool_call_start` | `{callId, name, arguments}` | LLM initiated a tool call |
| `tool_execution_start` | `{callId, name}` | Tool begins execution |
| `tool_execution_delta` | `{callId, line}` | Incremental tool output |
| `tool_execution_end` | `{callId, name, ok, exitCode}` | Tool finished |
| `turn_end` | `{reason}` | Agent turn completed |
| `done` | `{}` | Entire run finished |
| `error` | `{message, recoverable}` | Error occurred |

## Gateway Protocol

See `docs/protocol.md` for the full JSON-RPC specification.

## Tools Reference

| Tool | Description |
|------|-------------|
| `bash(command, timeout_seconds)` | Execute shell command |
| `read(path)` | Read a file |
| `write(path, content)` | Write a file |
| `edit(path, edits: [{oldText, newText}])` | Exact text replacement |
| `search(pattern, path)` | Recursive regex search |
| `list_dir(path)` | Directory listing |
| `load_skill(skill_name)` | Load a SKILL.md by name |
