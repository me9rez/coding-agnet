"""Entry point for the coding agent gateway.

Configuration is loaded from ``~/.coding-agent/settings.json``.
CLI flags and environment variables override file values.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from coding_agent.settings import Settings, resolve_api_key
from coding_agent.settings import load as load_settings
from coding_agent.tools.coding_tools import create_coding_tools

logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coding agent gateway")
    parser.add_argument("--log-level", default="WARNING", help="Logging level")
    parser.add_argument("--test", nargs="*", default=None, help="Run one prompt in CLI test mode")
    parser.add_argument("--model", default=None, help="Override model (default: settings.json)")
    parser.add_argument("--base-url", default=None, help="Override base URL (default: settings.json)")
    parser.add_argument("--thinking-level", default=None, help="Thinking level: off/low/medium/high")
    parser.add_argument("--ws-port", type=int, default=None, help="WebSocket port (WS mode instead of stdio)")
    return parser.parse_args(argv)

def _merge_settings(args: argparse.Namespace) -> Settings:
    """Load settings file, then apply CLI overrides."""
    s = load_settings()
    if args.model:
        s.model = args.model
    if args.base_url:
        s.base_url = args.base_url
    if args.thinking_level:
        s.thinking_level = args.thinking_level
    return s


def _build_client(settings: Settings) -> object:
    """Create the LLM client from settings."""
    api_key = resolve_api_key(settings)
    if api_key:
        from agent_framework_openai._chat_completion_client import RawOpenAIChatCompletionClient

        logger.info(
            "Client: model=%s base_url=%s thinking=%s", settings.model, settings.base_url, settings.thinking_level
        )
        return RawOpenAIChatCompletionClient(
            model=settings.model,
            base_url=settings.base_url,
            api_key=api_key,
        )

    logger.warning("No API key found, using fake client")
    return _FakeClient()


# ── Fake client for testing without API keys ────────────────────


class _FakeClient:
    """Minimal fake for testing the event pipeline without a real LLM."""

    async def get_response(self, messages: list[object], *, stream: bool = True, options: object = None) -> object:
        from agent_framework._types import ChatResponse, ChatResponseUpdate, Content, Message, ResponseStream

        if stream:

            async def _stream():
                yield ChatResponseUpdate(contents=[Content(type="text", text="Hello from fake agent! ")])
                yield ChatResponseUpdate(contents=[Content(type="text", text="No real API key configured.")])
                yield ChatResponseUpdate(finish_reason="stop")

            async def _finalizer(updates):
                texts = [u.text for u in updates if u.text]
                return ChatResponse(messages=[Message(role="assistant", contents=texts)], finish_reason="stop")

            return ResponseStream(_stream(), finalizer=_finalizer)

        return ChatResponse(
            messages=[Message(role="assistant", contents=["Hello from fake client!"])], finish_reason="stop"
        )


async def _run_test_mode(prompt: str, settings: Settings) -> None:
    """Run one prompt in CLI test mode, printing events to stderr."""
    from agent_framework._types import Message

    from coding_agent.loop import run_coding_agent
    from coding_agent.system_prompt import (
        BuildSystemPromptOptions,
        build_system_prompt,
        discover_project_context,
    )

    client = _build_client(settings)
    tools = create_coding_tools()
    messages: list[Message] = [Message(role="user", contents=[prompt])]
    ctx = discover_project_context()
    sys_prompt = build_system_prompt(BuildSystemPromptOptions(project_context=ctx))

    def on_event(event: object) -> None:
        line = json.dumps(
            {
                "type": type(event).__name__,
                **{k: v for k, v in vars(event).items() if v is not None and v != "" and k != "type"},
            },
            ensure_ascii=False,
            default=str,
        )
        print(line, file=sys.stderr, flush=True)

    print(f"User: {prompt}", file=sys.stderr)
    await run_coding_agent(
        client=client,  # type: ignore[arg-type]
        messages=messages,
        tools=tools,
        on_event=on_event,
        system_prompt=sys_prompt,
        thinking_level=settings.thinking_level or None,
        compaction_max_tokens=settings.max_context_tokens,
    )


class _StreamToLogger:
    def __init__(self) -> None:
        self._buf: list[str] = []

    def write(self, text: str) -> None:
        self._buf.append(text)
        if "\n" in text:
            for line in "".join(self._buf).splitlines(keepends=True):
                logger.debug("stdout guard: %s", line.rstrip())
            self._buf.clear()

    def flush(self) -> None:
        pass


async def _async_main(settings: Settings, ws_port: int | None = None) -> None:
    loop = asyncio.get_running_loop()
    orig_handler = loop.get_exception_handler()

    def _handler(_loop: asyncio.AbstractEventLoop, context: dict) -> None:
        exc = context.get("exception")
        if exc is not None and isinstance(exc, OSError) and exc.winerror == 6:
            return
        if orig_handler:
            orig_handler(_loop, context)
        else:
            loop.default_exception_handler(context)

    loop.set_exception_handler(_handler)

    from coding_agent.session import _SESSIONS_DIR
    print(f"Gateway starting, sessions → {_SESSIONS_DIR}", file=sys.stderr, flush=True)

    if ws_port:
        from coding_agent.gateway.ws_server import WsGatewayServer

        server = WsGatewayServer(
            client=_build_client(settings),
            tools=create_coding_tools(),
            settings=settings,
            port=ws_port,
        )
        await server.run_forever()
    else:
        from coding_agent.gateway.server import GatewayServer
        from coding_agent.gateway.transport import StdioTransport

        server = GatewayServer(
            client=_build_client(settings),
            tools=create_coding_tools(),
            transport=StdioTransport(),
            settings=settings,
        )
        await server.run()

def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.WARNING),
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    settings = _merge_settings(args)

    if args.test is not None:
        prompt = " ".join(args.test) or "Hello"
        asyncio.run(_run_test_mode(prompt, settings))
        return

    if args.ws_port:
        try:
            asyncio.run(_async_main(settings, ws_port=args.ws_port))
        except KeyboardInterrupt:
            pass
        return

    # stdio gateway mode (legacy)
    sys.stdout = _StreamToLogger()  # type: ignore[assignment]
    try:
        asyncio.run(_async_main(settings, ws_port=None))
    except KeyboardInterrupt:
        pass
