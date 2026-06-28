"""MCP server configuration and tool construction.

Reads the ``mcpServers`` section from ``~/.coding-agent/settings.json`` and
constructs ``agent_framework`` MCP tool wrappers for each configured server.
"""

from __future__ import annotations

import logging
from typing import Any

from coding_agent.settings import Settings

logger = logging.getLogger(__name__)


def format_mcp_tools_for_prompt(tools: list[Any]) -> str:
    """Format registered MCP tools for inclusion in the system prompt.

    This helps the model understand which MCP servers are available and when
    to use them.
    """
    if not tools:
        return ""

    lines = [
        "## Available MCP Servers",
        "",
        "The following external MCP servers are available. Their tools are listed below; "
        "use them when the user's request requires capabilities outside the local project "
        "(e.g. web search, external APIs).",
        "",
    ]
    for tool in tools:
        name = getattr(tool, "name", "unknown")
        description = getattr(tool, "description", "") or ""
        functions = getattr(tool, "functions", [])
        lines.append(f"- **{name}**: {description}")
        for func in functions:
            func_name = getattr(func, "name", "unknown")
            func_desc = getattr(func, "description", "")
            lines.append(f"  - `{func_name}`: {func_desc}")
        lines.append("")

    return "\n".join(lines)


def create_mcp_tools(settings: Settings) -> list[Any]:
    """Create MCP tool wrappers from settings.json ``mcpServers``.

    Example ``settings.json`` entries::

        {
          "mcpServers": {
            "filesystem": {
              "command": "npx",
              "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            },
            "exa": {
              "type": "streamable-http",
              "url": "https://mcp.exa.ai/mcp"
            }
          }
        }

    Parameters
    ----------
    settings:
        Loaded settings object.

    Returns
    -------
    List of ``MCPTool`` instances ready to be passed to ``Agent(tools=...)``.
    """
    from agent_framework import MCPStdioTool, MCPStreamableHTTPTool

    tools: list[Any] = []
    servers = getattr(settings, "mcp_servers", None) or {}
    if not isinstance(servers, dict):
        logger.warning("mcpServers is not a dict, skipping MCP tool creation")
        return tools

    for name, config in servers.items():
        if not isinstance(config, dict):
            logger.warning("MCP server %s config is not a dict, skipping", name)
            continue

        server_type = config.get("type", "stdio")
        description = config.get("description") or f"MCP server: {name}"
        allowed_tools = config.get("allowedTools")

        try:
            if server_type == "streamable-http":
                url = config.get("url")
                if not url:
                    logger.warning("MCP server %s missing 'url', skipping", name)
                    continue
                tool = MCPStreamableHTTPTool(
                    name=name,
                    url=str(url),
                    description=description,
                    allowed_tools=list(allowed_tools) if allowed_tools else None,
                )
                logger.info("Registered MCP server: %s (type=streamable-http, url=%s)", name, url)
            else:
                command = config.get("command")
                if not command:
                    logger.warning("MCP server %s missing 'command', skipping", name)
                    continue
                args = config.get("args") or []
                env = config.get("env")
                tool = MCPStdioTool(
                    name=name,
                    command=str(command),
                    args=[str(a) for a in args],
                    env={str(k): str(v) for k, v in env.items()} if env else None,
                    description=description,
                    allowed_tools=list(allowed_tools) if allowed_tools else None,
                )
                logger.info("Registered MCP server: %s (type=stdio, command=%s)", name, command)
            tools.append(tool)
        except Exception as exc:
            logger.warning("Failed to create MCP tool %s: %s", name, exc)

    return tools
