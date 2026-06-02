from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..policy import ContextPolicy
from ..schema import SelectedContext


@dataclass
class WrappedRunResult:
    content: str
    selected_context: SelectedContext
    agent_result: Any


class LightAgentContextWrapper:
    def __init__(self, agent: Any, context_policy: ContextPolicy):
        self.agent = agent
        self.context_policy = context_policy

    def run(
        self,
        *,
        session_id: str,
        user_id: str,
        current_message: str,
        raw_history: list[dict[str, Any]],
        available_tools: list[Any] | None = None,
        **agent_kwargs: Any,
    ) -> WrappedRunResult:
        selected = self.context_policy.select(
            session_id=session_id,
            user_id=user_id,
            current_message=current_message,
            raw_history=raw_history,
            available_tools=available_tools,
        )
        agent_result = self.agent.run(
            current_message,
            history=selected.messages,
            tools=selected.tools,
            user_id=user_id,
            result_format=agent_kwargs.pop("result_format", "object"),
            trace=agent_kwargs.pop("trace", True),
            **agent_kwargs,
        )
        content = getattr(agent_result, "content", str(agent_result))
        return WrappedRunResult(
            content=content,
            selected_context=selected,
            agent_result=agent_result,
        )
