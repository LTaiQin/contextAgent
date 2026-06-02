from __future__ import annotations

import re
from typing import Any


def tool_name(tool: Any) -> str:
    if callable(tool) and hasattr(tool, "tool_info"):
        return str(tool.tool_info.get("tool_name", getattr(tool, "__name__", "tool")))
    if isinstance(tool, dict):
        return str(tool.get("function", {}).get("name") or tool.get("name") or "tool")
    return str(tool)


class RuleBasedToolFilter:
    def filter(self, message: str, tools: list[Any] | None, need_type: str) -> list[Any]:
        tools = tools or []
        if not tools:
            return []
        if need_type == "tool_state":
            return tools
        if re.search(r"(weather|stock|search|browse|file|database|tool|api|天气|股票|搜索|文件)", message, re.I):
            return tools
        return []
