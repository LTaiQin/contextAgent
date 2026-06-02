from __future__ import annotations

import re

from .schema import GateDecision


HISTORY_REFERENCE_PATTERNS = [
    r"\b(previous|above|earlier|same as before|continue|that one|last one|the former)\b",
    r"(刚才|上一个|上一题|继续|按之前|照之前|那个|前面|上面|同样|沿用)",
]

TOOL_STATE_PATTERNS = [
    r"\b(cancel|reschedule|update|change|booked|reservation|order|ticket)\b",
    r"(取消|改签|修改|订单|预订|日程|工具状态)",
]

SELF_CONTAINED_PATTERNS = [
    r"\b(solve|find|calculate|prove|simplify|evaluate)\b[\s\S]{0,200}[=+\-*/^]",
    r"(求解|计算|证明|化简)[\s\S]{0,200}[=+\-*/^]",
    r"\bwhat is\b",
    r"\btranslate\b",
    r"(什么是|翻译)",
]


class RuleBasedNeedGate:
    def decide(self, message: str) -> GateDecision:
        text = message.strip()
        if self._has_history_reference(text):
            need_type = "tool_state" if self._has_tool_state_reference(text) else "task_local"
            return GateDecision(
                self_sufficient=False,
                needs_history=True,
                need_type=need_type,
                confidence=0.86,
                reason="Message explicitly refers to previous context.",
                missing_info=["referenced prior context"],
                risk_if_using_history="low",
            )
        if self._looks_self_contained(text):
            return GateDecision(
                self_sufficient=True,
                needs_history=False,
                need_type="no_context",
                confidence=0.88,
                reason="Message appears self-contained and has no explicit history reference.",
                risk_if_using_history="high",
            )
        if self._looks_ambiguous(text):
            return GateDecision(
                self_sufficient=False,
                needs_history=True,
                need_type="clarification",
                confidence=0.56,
                reason="Message contains an underspecified reference.",
                missing_info=["referent"],
                risk_if_using_history="medium",
            )
        return GateDecision(
            self_sufficient=True,
            needs_history=False,
            need_type="no_context",
            confidence=0.62,
            reason="No reliable evidence that history is required.",
            risk_if_using_history="medium",
        )

    def _has_history_reference(self, text: str) -> bool:
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in HISTORY_REFERENCE_PATTERNS)

    def _has_tool_state_reference(self, text: str) -> bool:
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in TOOL_STATE_PATTERNS)

    def _looks_self_contained(self, text: str) -> bool:
        if len(text) > 120:
            return True
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in SELF_CONTAINED_PATTERNS)

    def _looks_ambiguous(self, text: str) -> bool:
        return bool(re.search(r"\b(it|that|this|same)\b|这个|那个|一样", text, flags=re.IGNORECASE))
