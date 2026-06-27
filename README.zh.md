# Coding Agent

轻量级编码 agent，支持细粒度事件流、JSON-RPC 网关和 Vue TUI 终端界面。

## 架构

```
┌──────────────────────────────────────────────────────────────┐
│ Python 层                                                    │
│                                                              │
│  ┌─────────────────────┐   ┌─────────────────────────────┐   │
│  │ Agent Loop          │   │ 工具                        │   │
│  │ run_coding_agent()  │──▶│ bash, read, write,          │   │
│  │ 自定义 loop         │   │ edit, search, list_dir,     │   │
│  │ 发射细粒度事件       │   │ load_skill                  │   │
│  └─────────┬───────────┘   └─────────────────────────────┘   │
│            │                                                  │
│            ▼                                                  │
│  ┌─────────────────────────────────────┐                      │
│  │ WebSocket Gateway (JSON-RPC)       │                      │
│  │ ws_server.py — 监听 :8765           │                      │
│  │ {"method":"prompt",...}             │                      │
│  │ {"type":"text_delta",...}           │                      │
│  └──────────────────┬──────────────────┘                      │
│                     │ WebSocket 连接                          │
├─────────────────────┼────────────────────────────────────────┤
│ TypeScript 层        │                                         │
│                     ▼                                         │
│  ┌─────────────────────────────────────┐                      │
│  │ GatewayClient                       │                      │
│  │ gatewayClient.ts — WebSocket 客户端  │                      │
│  │ 读取消息，发送 JSON-RPC 请求         │                      │
│  └──────────────────┬──────────────────┘                      │
│                     │                                          │
│                     ▼                                          │
│  ┌─────────────────────────────────────┐                      │
│  │ Vue TUI (@simon_he/vue-tui)        │                      │
│  │ app.ts — 渲染函数组件                │                      │
│  │ main.ts — createTerminalApp 入口     │                      │
│  └─────────────────────────────────────┘                      │
└──────────────────────────────────────────────────────────────┘
```

**关键设计决策：**

- **自定义 agent loop**（不使用 `create_harness_agent`）：逐 chunk 发射 `thinking_delta`、`text_delta`、tool 生命周期事件，比 `AgentResponseUpdate` 粒度更细。
- **WebSocket 网关**：Python 以独立 WebSocket 服务器运行，TUI 通过 WebSocket 连接，不再管理子进程。
- **Vue TUI**：`@simon_he/vue-tui` 提供终端渲染，同时支持浏览器 DOM 和真实终端。

## 功能对照

| 功能 | 状态 |
|------|------|
| LLM provider: DeepSeek / OpenAI chat completions | ✅ |
| 事件流: text, thinking, tool call 生命周期 | ✅ |
| 工具: bash shell 执行 | ✅ |
| 工具: 文件读/写/编辑（精确替换） | ✅ |
| 工具: 文件搜索（递归 regex） | ✅ |
| 工具: 目录列表 | ✅ |
| 工具: skill 加载 | ✅ |
| System prompt 组装 | ✅ |
| 项目上下文发现 | ✅ |
| Session 持久化 (JSONL) | ✅ |
| Skills 系统 (SKILL.md) | ✅ |
| 上下文窗口压缩 (Compaction) | ✅ |
| Thinking level 控制 (off/low/medium/high) | ✅ |
| TUI: 消息折叠 (thinking/tool) | ✅ |
| TUI: token 用量显示 | ✅ |
| 多 provider 配置 | 🔲 |
| Session 分支切换 | 🔲 |

## 项目结构

```
coding-agent/
├── docs/
│   ├── proposal.md         # 原技术方案
│   ├── protocol.md         # Gateway JSON-RPC 协议规范
│   └── development.md      # 开发指南
├── python/
│   ├── pyproject.toml
│   └── src/coding_agent/
│       ├── __init__.py
│       ├── main.py          # 入口: gateway 模式 / --test CLI
│       ├── loop.py           # 自定义 agent loop
│       ├── events.py         # 8 种细粒度事件类型
│       ├── system_prompt.py  # System prompt 构建 + 项目上下文
│       ├── session.py        # JSONL session 持久化
│       ├── skills.py         # SKILL.md 扫描 + 渐进式加载
│       ├── compaction.py     # 上下文窗口压缩
│       ├── gateway/
│       │   ├── server.py     # stdio JSON-RPC dispatcher
│       │   ├── ws_server.py   # WebSocket gateway server
│       │   └── transport.py  # StdioTransport
│       └── tools/
│           └── coding_tools.py  # 全部工具实现
└── tui/
    ├── package.json
    ├── tsconfig.json
    ├── tsdown.config.ts
    └── src/
        ├── main.ts           # 终端 app 入口
        ├── app.ts            # Vue 渲染函数组件
        ├── gatewayClient.ts  # Python 子进程管理
        ├── gatewayTypes.ts   # 事件类型定义
        └── components/
            └── message-list.vue  # 遗留 Vue SFC（参考用）
```

## 快速开始

### 前置要求

- Python 3.14+
- Node.js 22+
- pnpm
- DeepSeek API key（或其他 OpenAI 兼容 API）

### 安装

```bash
# Python
cd python
uv sync

# TUI
cd ../tui
pnpm install
```

### 配置

所有配置集中在 `~/.coding-agent/settings.json`：

```bash
# 创建配置文件
python -c "
p = Path.home() / '.coding-agent'
p.mkdir(parents=True, exist_ok=True)
(p / 'settings.json').write_text('''{
  \"model\": \"deepseek-v4-flash\",
  \"base_url\": \"https://api.deepseek.com/v1\",
  \"api_key\": \"sk-xxx\",
  \"thinking_level\": \"medium\",
  \"max_context_tokens\": 1000000,
  \"max_output_tokens\": 384000,
  \"keep_recent_tokens\": 600000,
  \"max_turns\": 25
}''')
"
```

用户级 skill 放在 `~/.coding-agent/skills/`，项目级 skill 放在项目根目录 `skills/`。
### 运行

```bash
# CLI 测试模式（独立运行，无需网关）
cd python
uv run python -m coding_agent --test "列出 Python 文件"

# 终端 1：启动 Python WebSocket 网关
cd python
uv run python -m coding_agent --ws-port 8765

# 终端 2：启动 TUI（自动连接 ws://127.0.0.1:8765）
cd ../tui
pnpm dev
```


## 事件参考

| 事件 | 载荷 | 说明 |
|------|------|------|
| `thinking_delta` | `{delta}` | 推理 token（Anthropic） |
| `text_delta` | `{delta}` | 可见文本 token |
| `tool_call_start` | `{callId, name, arguments}` | LLM 发起工具调用 |
| `tool_execution_start` | `{callId, name}` | 工具开始执行 |
| `tool_execution_delta` | `{callId, line}` | 工具增量输出 |
| `tool_execution_end` | `{callId, name, ok, exitCode}` | 工具执行完成 |
| `turn_end` | `{reason}` | agent 轮次完成 |
| `done` | `{}` | 整个运行结束 |
| `error` | `{message, recoverable}` | 错误发生 |

## 工具参考

| 工具 | 说明 |
|------|------|
| `bash(command, timeout_seconds)` | 执行 shell 命令 |
| `read(path)` | 读取文件 |
| `write(path, content)` | 写入文件 |
| `edit(path, edits: [{oldText, newText}])` | 精确文本替换 |
| `search(pattern, path)` | 递归 regex 搜索 |
| `list_dir(path)` | 目录列表 |
| `load_skill(skill_name)` | 按名称加载 SKILL.md |
