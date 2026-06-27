# Coding Agent — 技术方案

## 1. 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│ Python: agent-framework (building blocks)                    │
│  ├─ BaseChatClient           LLM 流式调用                     │
│  ├─ FunctionTool             工具定义和执行                    │
│  ├─ ContextWindowCompactionStrategy  上下文压缩               │
│  └─ AgentSession             会话持久化                       │
├──────────────────────────────────────────────────────────────┤
│ Python: coding_agent (自定义 loop + gateway)                  │
│  ├─ loop.py                  自定义 agent loop                │
│  │   └─ BaseChatClient.get_response(stream=True)              │
│  │   └─ 每轮产出自定义细粒度事件流                             │
│  ├─ events.py                事件类型定义                      │
│  ├─ gateway/server.py        JSON-RPC dispatcher              │
│  └─ gateway/transport.py     StdioTransport                   │
├──────────────────────────────────────────────────────────────┤
│ TypeScript: GatewayClient                                     │
│  ├─ 管理 Python 子进程                                        │
│  ├─ stdin → JSON-RPC 请求                                     │
│  └─ stdout → JSON-RPC 事件流                                  │
├──────────────────────────────────────────────────────────────┤
│ Vue 3 + @simon_he/vue-tui (TUI)                              │
│  ├─ TAgentTranscript      transcript 容器                     │
│  ├─ TThinkingView         reasoning 展开/折叠                  │
│  ├─ TToolCallView         tool call 状态卡片                   │
│  ├─ TVirtualMarkdown      流式 markdown                       │
│  └─ TInput                输入面板                             │
└──────────────────────────────────────────────────────────────┘
```

### 为什么不用 `create_harness_agent`

`create_harness_agent` 打包了 `FunctionInvocationLayer + AgentLoopMiddleware`，但它的 streaming 事件粒度太粗——tool call 执行和 thinking delta 都被吞在内部。我们需要的不是 `AgentResponseUpdate(contents=[TextContent])`，而是：

| 事件 | 说明 | TUI 用途 |
|------|------|---------|
| `thinking_delta` | reasoning token 逐 chunk | `TThinkingView` 实时更新 |
| `text_delta` | 可见文本逐 chunk | `TVirtualMarkdown` 流式渲染 |
| `tool_call_start` | LLM 发起 tool call | `TToolCallView` 出现新卡片 |
| `tool_execution_start` | tool 开始执行 | 卡片显示 spinner / "Running..." |
| `tool_execution_delta` | tool 输出（stdout 行） | 卡片内实时日志 |
| `tool_execution_end` | tool 完成（exit code） | 卡片更新状态 |
| `turn_end` | 一轮 LLM+tool 完成 | transcript 换段 |

方案：用 `BaseChatClient.get_response(stream=True)` 自己做 loop，在每个点发射上述事件。

---

## 2. 事件粒度问题 vs 三种解决方案

### 问题重现

`FunctionInvocationLayer.get_response(stream=True)` 内部循环：

```python
# _tools.py:2711-2768
async def _stream():
    for attempt in range(max_iterations):
        inner_stream = super_get_response(messages, stream=True, ...)  # ← LLM 调用
        async for update in inner_stream:
            yield update                                           # ← 只 yield text delta
        
        response = await inner_stream.get_final_response()
        # tool call 在这里执行，但外部 stream 无感知
        result = await _process_function_requests(response, ...)    # ← 静默执行
        if result.get("action") == "continue":
            continue                                                # ← 下一轮 LLM 调用
```

external stream 看到的是：

```
ChatResponseUpdate(text="让我查一下...")
ChatResponseUpdate(text="用 Python 的话...")
→ [静默: tool call → execute bash → 拿结果 → 再调 LLM]
ChatResponseUpdate(text="结果出来了...")
```

中间缺失：thinking delta、tool call 开始/执行/结束。

### 方案 A：`raw_representation` 提取

`ChatResponseUpdate` 和 `Content` 都有 `raw_representation` 字段，provider SDK 原生对象留在这里。

```python
raw = update.raw_representation  # Anthropic: MessageDeltaEvent
if raw and getattr(raw, "type", None) == "content_block_delta":
    if raw.delta.type == "thinking":
        emit("thinking_delta", delta=raw.delta.thinking)
    elif raw.delta.type == "text":
        emit("text_delta", delta=raw.delta.text)
```

**优点**：零改 agent-framework，纯 gateway 层过滤  
**缺点**：`raw_representation` 格式 provider 相关，需适配每个 provider；thinking 只在 Anthropic 类 provider 上有

### 方案 B：自定义 loop + `BaseChatClient`（推荐）

不用 `create_harness_agent`，直接用 `BaseChatClient.get_response()` 自己做 loop：

```python
# loop.py（~400 行）
async def run_coding_agent(client, messages, tools, on_event):
    """Coding agent loop 发射细粒度事件到 TUI。"""
    tools = normalize_tools(tools)
    tool_map = {t.name: t for t in tools}
    
    while True:
        # 1. LLM streaming → 逐 token 事件
        stream = client.get_response(messages, stream=True, options=dict(tools=tools))
        pending_calls = []
        
        async for update in stream:
            # 1a. raw_representation → thinking delta
            raw = update.raw_representation
            if raw and getattr(raw, "type", None) == "content_block_delta":
                if raw.delta.type == "thinking":
                    on_event(ThinkingDeltaEvent(delta=raw.delta.thinking))
            
            # 1b. content → text delta / tool call
            for c in update.contents or []:
                if c.type == "text":
                    on_event(TextDeltaEvent(delta=c.text))
                elif c.type == "function_call":
                    on_event(ToolCallStartEvent(name=c.name, call_id=c.call_id))
                    pending_calls.append(c)
        
        response = await stream.get_final_response()
        
        # 2. 无 tool call → 结束
        if not pending_calls:
            on_event(TurnEndEvent(reason="complete"))
            break
        
        # 3. 执行 tool call
        for tc in pending_calls:
            on_event(ToolExecutionStartEvent(call_id=tc.call_id, name=tc.name))
            result = await execute_tool(tc, tool_map)
            if result.streaming:
                async for line in result.streaming:
                    on_event(ToolExecutionDeltaEvent(call_id=tc.call_id, line=line))
            on_event(ToolExecutionEndEvent(call_id=tc.call_id, ok=result.ok))
            messages.append(result.to_message())
        
        on_event(TurnEndEvent(reason="tool_calls"))
```

**优点**：完全控制事件粒度，所有事件在正确时机发射，不依赖 provider 特定格式  
**缺点**：约 400 行额外代码；需自行接入 compaction 和 session（agent-framework 组件可复用）

### 方案 C：自定义 `AgentMiddleware` 拦截流

在 middleware 链中拦截 `ResponseStream`，重新包装：

```python
class FineGrainedEventMiddleware(AgentMiddleware):
    async def process_response(self, response, context):
        if not isinstance(response, ResponseStream):
            return response
        # 从 raw_representation 提取 thinking delta
        # 注入到 additional_properties，gateway 再提取
```

**优点**：保留 `create_harness_agent` 全功能  
**缺点**：middleware 层在 agent-framework 内部限制较多，still depends on `raw_representation`

### 对比

| 维度 | 方案 A | 方案 B | 方案 C |
|------|--------|--------|--------|
| 实现成本 | ~50 行 | ~400 行 | ~100 行 |
| 事件完整度 | 仅 text + thinking | 全部 | 部分 |
| provider 依赖 | 高（raw 格式） | 低（原始 Content 解析） | 中 |
| 控制力 | 弱 | 最强 | 中 |
| agent-framework 复用 | 全量 | building blocks | 全量 |

**结论：选方案 B**。编码 agent 的事件粒度是核心 UX 差异点，值得这 ~400 行。

---

## 3. Gateway JSON-RPC 协议

### 通信方式

Python gateway 进程通过 stdio 与 TS TUI 通信，newline-delimited JSON-RPC。

### 事件流（gateway → TUI）

```
{"type":"thinking_delta","delta":"..."}
{"type":"text_delta","delta":"..."}
{"type":"tool_call_start","call_id":"call_1","name":"bash"}
{"type":"tool_execution_start","call_id":"call_1","status":"running"}
{"type":"tool_execution_delta","call_id":"call_1","line":"$ ls\n"}
{"type":"tool_execution_end","call_id":"call_1","exit_code":0}
{"type":"turn_end","reason":"tool_calls"}
{"type":"text_delta","delta":"结果是..."}
{"type":"done"}
```

### 请求流（TUI → gateway）

```
{"method":"prompt","params":{"text":"写一个 Python 脚本"}}
{"method":"cancel","params":{}}
{"method":"provider","params":{"name":"openai","model":"gpt-4o"}}
```

---

## 4. 目录结构

```
coding-agent/
├── README.md                    # 项目说明
├── docs/proposal.md             # 本文
│
├── python/
│   ├── pyproject.toml           # 依赖: agent-framework, agent-framework-tools
│   └── src/
│       └── coding_agent/
│           ├── __init__.py
│           ├── main.py          # 入口: argparse → gateway.run()
│           ├── events.py        # 细粒度事件类型
│           ├── loop.py          # 自定义 agent loop (方案 B)
│           ├── gateway/
│           │   ├── __init__.py
│           │   ├── server.py    # dispatch: 读写 stdio, 路由事件
│           │   └── transport.py # StdioTransport (newline JSON)
│           └── tools/
│               ├── __init__.py
│               └── coding_tools.py  # shell, file 等工具
│
└── tui/
    ├── package.json              # 依赖: @simon_he/vue-tui, typescript
    ├── tsconfig.json
    ├── src/
    │   ├── App.vue               # 根组件
    │   ├── gatewayClient.ts      # 管理 Python 子进程 + JSON-RPC
    │   ├── gatewayTypes.ts       # 事件类型定义
    │   └── components/
    │       ├── AgentConsole.vue  # main layout: transcript + input
    │       ├── Transcript.vue    # TAgentTranscript 容器
    │       ├── ThinkingArea.vue  # TThinkingView
    │       ├── ToolCallCard.vue  # TToolCallView
    │       └── UserInput.vue     # TInput
    ├── index.html
    └── vite.config.ts
```

---

## 5. 各层关键接口

### Python: `events.py`

```python
@dataclass
class ThinkingDeltaEvent:    delta: str

@dataclass
class TextDeltaEvent:        delta: str

@dataclass
class ToolCallStartEvent:    call_id: str; name: str; args: dict

@dataclass
class ToolExecutionStartEvent:    call_id: str; name: str

@dataclass
class ToolExecutionDeltaEvent:    call_id: str; line: str

@dataclass
class ToolExecutionEndEvent:      call_id: str; ok: bool; exit_code: int | None

@dataclass
class TurnEndEvent:         reason: str  # "complete" | "tool_calls"

@dataclass
class DoneEvent:            pass
```

### Python: `loop.py` 核心签名

```python
async def run_coding_agent(
    client: BaseChatClient,
    messages: list[Message],
    tools: list[FunctionTool],
    on_event: Callable[[AgentEvent], None],
    *,
    max_turns: int = 25,
    compaction_strategy: CompactionStrategy | None = None,
    tokenizer: TokenizerProtocol | None = None,
) -> None
```

### Python: `transport.py`

```python
class StdioTransport:
    def write(self, obj: dict) -> bool   # JSON.dumps → sys.stdout + \n
    def close(self) -> None              # flush + cleanup
```

### Python: `gateway/server.py`

```python
class GatewayServer:
    def __init__(self, transport: Transport): ...
    async def run(self): ...             # 读取 stdin JSON-RPC → 派发
```

### TypeScript: `gatewayTypes.ts`

```typescript
export type GatewayEvent =
  | { type: 'thinking_delta'; delta: string }
  | { type: 'text_delta'; delta: string }
  | { type: 'tool_call_start'; callId: string; name: string }
  | { type: 'tool_execution_start'; callId: string; name: string }
  | { type: 'tool_execution_delta'; callId: string; line: string }
  | { type: 'tool_execution_end'; callId: string; ok: boolean; exitCode?: number }
  | { type: 'turn_end'; reason: string }
  | { type: 'done' }

export type GatewayRequest =
  | { method: 'prompt'; params: { text: string } }
  | { method: 'cancel'; params: Record<string, never> }
```

### TypeScript: `gatewayClient.ts`

```typescript
class GatewayClient {
  start(): void              // spawn Python subprocess
  send(req: GatewayRequest): void   // write to stdin
  onEvent(cb: (ev: GatewayEvent) => void): void
  stop(): void               // kill subprocess
}
```

### Vue TUI 组件组合

```vue
<TerminalProvider :cols="120" :rows="40">
  <TRenderPlane name="transcript">
    <TAgentTranscript>
      <TThinkingView v-for="t in thinking" />
      <TToolCallView v-for="tc in toolCalls" />
      <TVirtualMarkdown :source="markdown" />
    </TAgentTranscript>
  </TRenderPlane>
  <TRenderPlane name="input">
    <TInput v-model="input" @submit="onSubmit" />
  </TRenderPlane>
</TerminalProvider>
```

---

## 6. 开发路线

### Phase 1：Python loop + CLI 验证（~2d）

- `events.py` + `loop.py`：自定义 loop，emit 到控制台（print JSON）
- `transport.py`：StdioTransport
- 验证：用 `OpenAIChatClient` 跑一次 agent 对话，能看到逐 token thinking 和 tool call 生命周期

### Phase 2：Gateway + Vue TUI 原型（~2d）

- `gateway/server.py`：读取 stdin JSON-RPC，派发 prompt/cancel
- `gatewayClient.ts`：spawn 子进程，读取 stdout 事件
- `App.vue`：拼 TAgentTranscript + TInput，连接 gatewayClient

### Phase 3：工具 + 配置 + 产品化（~3d）

- `coding_tools.py`：shell, file read/write, search
- Provider 切换、session 持久化
- 错误处理、子进程管理、Ctrl+C 清理

---

## 7. 核心依赖

| 层 | 依赖 | 用途 |
|----|------|------|
| Python | `agent-framework` + `agent-framework-tools` | BaseChatClient, FunctionTool, CompactionStrategy |
| Python | `agent-framework-openai` 或 `agent-framework-claude` | Provider client |
| Python | `pydantic` | 事件类型（可选） |
| TUI | `@simon_he/vue-tui` | Terminal UI 组件 |
| TUI | `@simon_he/vue-tui/agent` | TAgentTranscript, TThinkingView, TToolCallView |
| TUI | `@simon_he/vue-tui/cli` | createTerminalApp, createStdoutRenderer |
| TUI | `typescript` | 类型安全 |
