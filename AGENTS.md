# Coding Agent — AGENTS.md

## 仓库结构

两包 monorepo，根目录无直接代码：

- `python/` — agent 核心（自定义 loop + 工具 + gateway），Python 3.14+
- `tui/` — 终端 UI（Vue TUI + gateway client），Node 22+, pnpm
- 必须 `cd` 进对应目录再执行命令

## Python 层

```bash
cd python
uv sync                    # 安装依赖
ruff check src/            # lint
ruff format --check src/   # 格式化检查
pyright src/               # 类型检查 (pyright)
```

- 构建系统：hatchling，依赖管理：uv（不是 pip）
- Ruff 配置：line-length 120，双引号，target py314
- 无测试框架，无测试目录。测试方式：
  - `_FakeClient`（`main.py:68`）—— 无需 API key 的 fake，验证 event pipeline
  - `python -m coding_agent.main --test "prompt"` —— 集成测试，需要真实 API key
- Python 入口：`coding_agent.main:main`
- 包名 `coding_agent`，源码在 `python/src/`，必须让 PYTHONPATH 包含此路径
- API key 优先级：settings.json > `DEEPSEEK_API_KEY` 环境变量 > `OPENAI_API_KEY`
- 添加工具：在 `tools/coding_tools.py` 写 async 函数，在 `create_coding_tools()` 注册 `FunctionTool`，参数名和 docstring 自动转 JSON schema

## TUI 层

```bash
cd tui
pnpm install               # 安装依赖
pnpm dev                   # 开发运行（tsx 直接执行，无需构建）
pnpm type-check            # tsc --noEmit 类型检查
pnpm build                 # tsdown 构建到 dist/
pnpm start                 # 运行构建产物
```

- TUI 入口：`src/main.ts`（`createTerminalApp` + `@simon_he/vue-tui`）
- `gatewayClient.ts` 中 `pythonSrc` 硬编码为 `C:/code/repo/coding-agent/python/src` —— 仓库路径变更时需要更新
- 网关协议：stdin/stdout 上的 newline-delimited JSON（详见 `docs/protocol.md`）

## 配置

所有配置在 `~/.coding-agent/settings.json`，支持 model/base_url/api_key/thinking_level/token budgets/max_turns。

用户 skill 在 `~/.coding-agent/skills/`，项目 skill 在根 `skills/`。

## 打包与发布

web 前端构建产物会随 Python wheel 一起分发，用户安装后即可通过 `coding-agent --web` 直接运行。

```powershell
# 一键构建 whl（含 web/dist）
.\scripts\build-package.ps1

# 本地测试安装
uv tool install --reinstall python/dist/coding_agent-*.whl
coding-agent --web

# 构建并发布到 PyPI（需配置 UV_PUBLISH_TOKEN 或 PyPI 凭证）
.\scripts\build-package.ps1 -Publish
```

- 包名与入口脚本在 `python/pyproject.toml` 中定义。
- 运行时会优先使用 wheel 内嵌的 `coding_agent/web_dist` 资源，开发环境回退到 `web/dist`。

## 无 CI / 无 pre-commit

仓库没有 CI 配置或 pre-commit hook。修改后手动运行：
1. `ruff check src/`（Python lint）
2. `pnpm type-check`（TUI 类型检查）
3. `python -m coding_agent.main --test "..."`（集成测试验证）
