from __future__ import annotations

from typing import Any


class PromptAssembler:
    def assemble_messages(self, selected_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(selected_history)

    def system_addendum(self, policy_name: str) -> str:
        if policy_name == "task_scoped":
            return "Use only the selected context. Ignore unrelated prior tasks."
        return ""
