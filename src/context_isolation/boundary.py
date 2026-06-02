from __future__ import annotations

import re

from .schema import BoundaryDecision, GateDecision


TOOL_STATE_HISTORY_PATTERNS = [
    r"\b(cancel|reschedule|update|change|booked|reservation|order|ticket|calendar|reminder|flight)\b",
    r"(取消|改签|修改|订单|预订|日程|提醒|航班|机票)",
]


class RuleBasedBoundaryDetector:
    def decide(self, raw_history: list[dict], gate: GateDecision) -> BoundaryDecision:
        if not gate.needs_history:
            return BoundaryDecision(
                boundary="new_task",
                task_id=None,
                confidence=gate.confidence,
                reason="Need gate marked the message as self-contained.",
            )
        if not raw_history:
            return BoundaryDecision(
                boundary="ambiguous",
                task_id=None,
                confidence=0.5,
                reason="Message refers to context, but no history exists.",
            )
        active_task_id = raw_history[-1].get("task_id")
        candidate_task_ids = []
        for message in raw_history:
            task_id = message.get("task_id")
            if task_id and task_id not in candidate_task_ids:
                candidate_task_ids.append(task_id)
        if gate.need_type == "tool_state":
            tool_task_id = self._latest_tool_state_task_id(raw_history)
            if tool_task_id:
                return BoundaryDecision(
                    boundary="continue_task",
                    task_id=str(tool_task_id),
                    confidence=0.78,
                    reason="Tool-state reference resolved to the latest task with tool-state evidence.",
                    candidate_task_ids=candidate_task_ids,
                )
        if active_task_id:
            return BoundaryDecision(
                boundary="continue_task",
                task_id=str(active_task_id),
                confidence=0.82,
                reason="Explicit reference resolved to the latest active task.",
                candidate_task_ids=candidate_task_ids,
            )
        return BoundaryDecision(
            boundary="continue_task",
            task_id=None,
            confidence=0.68,
            reason="Explicit reference resolved to recent unlabelled history.",
            candidate_task_ids=candidate_task_ids,
        )

    def _latest_tool_state_task_id(self, raw_history: list[dict]) -> str | None:
        for message in reversed(raw_history):
            content = str(message.get("content", ""))
            if any(re.search(pattern, content, flags=re.IGNORECASE) for pattern in TOOL_STATE_HISTORY_PATTERNS):
                task_id = message.get("task_id")
                if task_id:
                    return str(task_id)
        return None
