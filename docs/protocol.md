# Gateway JSON-RPC Protocol

The coding agent gateway communicates with the TUI over **stdin/stdout** using **newline-delimited JSON** (one JSON object per line, terminated by `\n`).

The TUI spawns the Python process as a subprocess:
```
TUI ──stdin──→ {"method":"prompt","params":{"text":"..."}}
TUI ←─stdout── {"type":"text_delta","delta":"..."}
TUI ←─stdout── {"type":"done"}
```

## Startup

On startup, the gateway emits a `ready` event:

```
← {"type":"ready"}
```

This signals the TUI that the gateway is initialized and ready to accept requests.

## Events (gateway → TUI)

### text_delta
```json
{"type":"text_delta","delta":"Hello, world!"}
```
A visible text token emitted during model streaming.

### thinking_delta
```json
{"type":"thinking_delta","delta":"The user wants to..."}
```
A reasoning/thinking token (typically from Anthropic or similar providers that support extended thinking).

### tool_call_start
```json
{"type":"tool_call_start","callId":"call_xxx","name":"bash","arguments":"{\"command\":\"ls\"}"}
```
The LLM has initiated a tool call. All arguments are available in the `arguments` JSON string.

### tool_execution_start
```json
{"type":"tool_execution_start","callId":"call_xxx","name":"bash"}
```
A tool call begins execution.

### tool_execution_delta
```json
{"type":"tool_execution_delta","callId":"call_xxx","line":"file1.py\n"}
```
Incremental output from a running tool (e.g., stdout lines from a shell command).

### tool_execution_end
```json
{"type":"tool_execution_end","callId":"call_xxx","name":"bash","ok":true,"exitCode":0}
```
A tool call has finished execution. `ok` indicates success; `exitCode` is the process exit code.

### turn_end
```json
{"type":"turn_end","reason":"complete"}
```
```json
{"type":"turn_end","reason":"tool_calls"}
```
One agent turn completed. `reason` indicates:
- `complete`: no more tool calls needed, final response ready
- `tool_calls`: tool call(s) will follow

### done
```json
{"type":"done"}
```
The entire agent run is finished. The TUI should return to idle state.

### error
```json
{"type":"error","message":"Agent run cancelled","recoverable":true}
```
```json
{"type":"error","message":"Connection failed","recoverable":false}
```
An error occurred. `recoverable: true` means the agent may continue; `false` means the run should stop.

## Requests (TUI → gateway)

### prompt
```json
{"method":"prompt","params":{"text":"List Python files"}}
```
```json
{"method":"prompt","params":{"text":"Continue","sessionId":"abc123"}}
```
Send a user message to the agent. If `sessionId` is provided, the gateway resumes that session.

### cancel
```json
{"method":"cancel","params":{}}
```
Cancel the current agent run. The gateway will emit an `error` event with `recoverable: true`.

## Example Conversation

```
TUI → {"method":"prompt","params":{"text":"echo hello"}}

TUI ← {"type":"text_delta","delta":"Let"}
TUI ← {"type":"text_delta","delta":" me"}
TUI ← {"type":"text_delta","delta":" run"}
TUI ← {"type":"text_delta","delta":" that..."}
TUI ← {"type":"turn_end","reason":"tool_calls"}
TUI ← {"type":"tool_call_start","callId":"call_1","name":"bash","arguments":"{\"command\":\"echo hello\"}"}
TUI ← {"type":"tool_execution_start","callId":"call_1","name":"bash"}
TUI ← {"type":"tool_execution_end","callId":"call_1","name":"bash","ok":true,"exitCode":0}
TUI ← {"type":"text_delta","delta":"Done!"}
TUI ← {"type":"turn_end","reason":"complete"}
TUI ← {"type":"done"}
```
