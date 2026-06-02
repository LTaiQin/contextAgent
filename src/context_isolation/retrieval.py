from __future__ import annotations


class ScopedRetriever:
    def __init__(self, max_turns: int = 6):
        self.max_turns = max_turns

    def retrieve(self, raw_history: list[dict], task_id: str | None, need_type: str) -> list[dict]:
        if need_type == "no_context":
            return []
        if not raw_history:
            return []
        if task_id:
            selected = [message for message in raw_history if message.get("task_id") == task_id]
            return selected[-self.max_turns :]
        return list(raw_history[-self.max_turns :])
