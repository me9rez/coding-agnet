# 开发指南

## Python 层

### 依赖

agent 使用 `agent-framework`（Microsoft Agent Framework）作为 LLM 客户端层。
core 和 openai 包从本地克隆以 editable 模式安装：

```bash
cd python
uv venv
uv pip install -e "../../agent-framework/python/packages/core" --no-deps
uv pip install -e "../../agent-framework/python/packages/openai" --no-deps
uv pip install pydantic httpx openai python-dotenv
```

### 运行

```bash
# CLI 测试模式 — 事件打印到 stderr
.venv/Scripts/python -m coding_agent.main --test "你的提示词"

# CLI 测试模式 + 自定义模型
.venv/Scripts/python -m coding_agent.main --test "Hello" --model deepseek-chat --base-url https://api.deepseek.com/v1

# Gateway 模式 — 等待 TUI 连接
.venv/Scripts/python -m coding_agent.main
```

### 添加新工具

1. 在 `tools/coding_tools.py` 中创建 async 函数
2. 在 `create_coding_tools()` 中注册为 `FunctionTool` 实例
3. 函数的参数名和 docstring 自动转换为 JSON schema

示例：

```python
async def _my_tool(param1: str, param2: int = 42) -> str:
    """工具功能描述。"""
    return f"结果: {param1}, {param2}"

# 在 create_coding_tools() 中：
FunctionTool(name="my_tool", description="工具描述", func=_my_tool),
```

## TUI 层

### 依赖

TUI 使用 `@simon_he/vue-tui` 进行终端渲染，`tsdown` 进行构建。

```bash
cd tui
npm install
```

### 开发流程

```bash
# 类型检查
npm run type-check

# 构建
npm run build      # tsdown

# 开发（构建 + 运行）
npm run dev        # 构建后立即执行
```

### 架构

TUI 是单页终端应用，包含：

- **main.ts**: 入口 — 创建 terminal app、stdout renderer、stdin driver
- **app.ts**: 渲染函数组件 — 使用 `h()` 调用构建 UI 树
- **gatewayClient.ts**: 管理 Python 子进程 — 启动、读 stdout、写 stdin
- **gatewayTypes.ts**: 所有 gateway 事件的 TypeScript 类型定义

### 组件层次

```
createTerminalApp() → 挂载 App 组件
  └── App (渲染函数)
      ├── 标题栏 (TText)
      ├── 分隔线 (TText)
      ├── 消息列表 (每条消息一个 TBox)
      │   ├── 用户文本 (TBox + TText)
      │   ├── 助手文本 (TBox + TText)
      │   ├── Thinking 块 (TBox + TText, 可折叠)
      │   ├── 工具执行 (TBox + TText, 可折叠)
      │   └── 错误 (TBox + TText)
      ├── 流式区域 (TBox + TText)
      ├── 状态指示 (TText)
      ├── Token 栏 (TText)
      └── 输入行 (TBox + TText)
```

### 事件流

```
GatewayEvent → handleEvent() → transcript[] / streaming / token count
                              → render() → VNode tree → 终端输出
```

## 测试

### Python 单元测试

```python
import asyncio
from agent_framework._types import Message
from coding_agent.tools.coding_tools import create_coding_tools
from coding_agent.loop import run_coding_agent

# 使用 fake client（无需 API key）
from coding_agent.main import _FakeClient

async def test():
    client = _FakeClient()
    messages = [Message(role="user", contents=["Hello"])]
    tools = create_coding_tools()
    events = []
    await run_coding_agent(client, messages, tools, on_event=events.append)
    print(f"生成了 {len(events)} 个事件")

asyncio.run(test())
```

### 完整集成测试

需要 `DEEPSEEK_API_KEY` 环境变量：

```bash
cd python
.venv/Scripts/python -m coding_agent.main --test "执行 echo hello"
```

## 常见问题

### "No module named 'coding_agent'"

确保 `PYTHONPATH` 包含 `python/src`，或者从 `python/` 目录运行。

### TUI 显示 "Cannot find module"

先执行 `npm install`，然后执行 `npm run build`。

### Python 子进程 "module not found"

TUI 在 `gatewayClient.ts` 中自动设置 `PYTHONPATH`。如果路径不同，更新 `pythonSrc` 变量。

### 更新依赖后出现类型错误

tsconfig 使用严格模式。执行 `npx tsc --noEmit` 并修复报告的问题。
