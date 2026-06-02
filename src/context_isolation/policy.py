from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from time import perf_counter
from typing import Any

from .assembler import PromptAssembler
from .boundary import RuleBasedBoundaryDetector
from .evidence import EvidenceValidator
from .gates import RuleBasedNeedGate
from .retrieval import ScopedRetriever
from .schema import ContextDecision, SelectedContext
from .tool_filter import RuleBasedToolFilter


def _message_id(message: dict[str, Any], index: int) -> str:
    return str(message.get("turn_id") or message.get("id") or f"turn_{index}")


def _tool_name(tool: Any) -> str:
    if callable(tool) and hasattr(tool, "tool_info"):
        return str(tool.tool_info.get("tool_name", getattr(tool, "__name__", "tool")))
    if isinstance(tool, dict):
        return str(tool.get("function", {}).get("name") or tool.get("name") or "tool")
    return str(tool)


def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
    chars = sum(len(str(message.get("content", ""))) for message in messages)
    return max(1, round(chars / 3.5)) if chars else 0


class ContextPolicy(ABC):
    name = "base"

    @abstractmethod
    def select(
        self,
        session_id: str,
        user_id: str,
        current_message: str,
        raw_history: list[dict[str, Any]],
        available_tools: list[Any] | None = None,
    ) -> SelectedContext:
        ...

    def _build_selected(
        self,
        *,
        session_id: str,
        user_id: str,
        current_message: str,
        raw_history: list[dict[str, Any]],
        selected_history: list[dict[str, Any]],
        available_tools: list[Any] | None,
        selected_tools: list[Any] | None,
        decision: ContextDecision,
        started_at: float,
        system_addendum: str = "",
    ) -> SelectedContext:
        selected_tools = selected_tools or []
        all_tool_names = [_tool_name(tool) for tool in available_tools or []]
        selected_tool_names = [_tool_name(tool) for tool in selected_tools]
        decision.selected_tools = selected_tool_names
        decision.suppressed_tools = [name for name in all_tool_names if name not in set(selected_tool_names)]

        trace = {
            "session_id": session_id,
            "user_id": user_id,
            "policy": self.name,
            "current_message_chars": len(current_message),
            "raw_history_count": len(raw_history),
            "selected_history_count": len(selected_history),
            "input_tokens_est": _estimate_tokens(selected_history + [{"role": "user", "content": current_message}]),
            "decision_latency_ms": round((perf_counter() - started_at) * 1000, 3),
            "decision": asdict(decision),
        }
        return SelectedContext(
            system_addendum=system_addendum,
            messages=selected_history,
            memories=[],
            tools=selected_tools,
            trace=trace,
            decision=decision,
        )


class FullSessionPolicy(ContextPolicy):
    name = "full_session"

    def select(
        self,
        session_id: str,
        user_id: str,
        current_message: str,
        raw_history: list[dict[str, Any]],
        available_tools: list[Any] | None = None,
    ) -> SelectedContext:
        started_at = perf_counter()
        selected_turn_ids = [_message_id(message, index) for index, message in enumerate(raw_history)]
        decision = ContextDecision(
            self_sufficient=False,
            need_type="task_local",
            boundary="continue_task",
            task_id=raw_history[-1].get("task_id") if raw_history else None,
            confidence=1.0,
            selected_turn_ids=selected_turn_ids,
            reason="Baseline policy: expose the full session history.",
        )
        return self._build_selected(
            session_id=session_id,
            user_id=user_id,
            current_message=current_message,
            raw_history=raw_history,
            selected_history=list(raw_history),
            available_tools=available_tools,
            selected_tools=available_tools or [],
            decision=decision,
            started_at=started_at,
        )


class RecentNPolicy(ContextPolicy):
    name = "recent_n"

    def __init__(self, n: int = 4):
        self.n = n

    def select(
        self,
        session_id: str,
        user_id: str,
        current_message: str,
        raw_history: list[dict[str, Any]],
        available_tools: list[Any] | None = None,
    ) -> SelectedContext:
        started_at = perf_counter()
        selected_history = list(raw_history[-self.n :]) if self.n > 0 else []
        offset = max(0, len(raw_history) - len(selected_history))
        selected_turn_ids = [_message_id(message, offset + index) for index, message in enumerate(selected_history)]
        decision = ContextDecision(
            self_sufficient=False,
            need_type="task_local",
            boundary="continue_task",
            task_id=selected_history[-1].get("task_id") if selected_history else None,
            confidence=1.0,
            selected_turn_ids=selected_turn_ids,
            reason=f"Baseline policy: expose the most recent {self.n} turns.",
        )
        return self._build_selected(
            session_id=session_id,
            user_id=user_id,
            current_message=current_message,
            raw_history=raw_history,
            selected_history=selected_history,
            available_tools=available_tools,
            selected_tools=available_tools or [],
            decision=decision,
            started_at=started_at,
        )


class RetrievalOnlyPolicy(ContextPolicy):
    name = "retrieval_only"

    def __init__(self, top_k: int = 4):
        self.top_k = top_k

    def select(
        self,
        session_id: str,
        user_id: str,
        current_message: str,
        raw_history: list[dict[str, Any]],
        available_tools: list[Any] | None = None,
    ) -> SelectedContext:
        started_at = perf_counter()
        selected_history = self._retrieve_by_overlap(current_message, raw_history)
        selected_turn_ids = [
            _message_id(message, raw_history.index(message)) for message in selected_history if message in raw_history
        ]
        decision = ContextDecision(
            self_sufficient=False,
            need_type="task_local",
            boundary="related_task" if selected_history else "new_task",
            task_id=selected_history[-1].get("task_id") if selected_history else None,
            confidence=0.7 if selected_history else 0.5,
            selected_turn_ids=selected_turn_ids,
            reason=f"Baseline policy: retrieve top {self.top_k} turns by lexical overlap.",
        )
        return self._build_selected(
            session_id=session_id,
            user_id=user_id,
            current_message=current_message,
            raw_history=raw_history,
            selected_history=selected_history,
            available_tools=available_tools,
            selected_tools=available_tools or [],
            decision=decision,
            started_at=started_at,
        )

    def _retrieve_by_overlap(self, current_message: str, raw_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        query_terms = self._terms(current_message)
        scored = []
        for index, message in enumerate(raw_history):
            content_terms = self._terms(str(message.get("content", "")))
            score = len(query_terms & content_terms)
            if score:
                scored.append((score, index, message))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [message for _, _, message in scored[: self.top_k]]

    def _terms(self, text: str) -> set[str]:
        import re

        return {token.lower() for token in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text)}


class NeedGatedPolicy(ContextPolicy):
    name = "need_gated"

    def __init__(self, max_turns: int = 6):
        self.need_gate = RuleBasedNeedGate()
        self.retriever = ScopedRetriever(max_turns=max_turns)
        self.evidence_validator = EvidenceValidator()

    def select(
        self,
        session_id: str,
        user_id: str,
        current_message: str,
        raw_history: list[dict[str, Any]],
        available_tools: list[Any] | None = None,
    ) -> SelectedContext:
        started_at = perf_counter()
        gate = self.need_gate.decide(current_message)
        task_id = raw_history[-1].get("task_id") if raw_history and gate.needs_history else None
        candidates = self.retriever.retrieve(raw_history, task_id, gate.need_type)
        selected_history = self.evidence_validator.validate(current_message, candidates, gate.need_type)
        selected_turn_ids = [
            _message_id(message, raw_history.index(message)) for message in selected_history if message in raw_history
        ]
        decision = ContextDecision(
            self_sufficient=gate.self_sufficient,
            need_type=gate.need_type,
            boundary="continue_task" if selected_history else "new_task",
            task_id=task_id,
            confidence=gate.confidence,
            selected_turn_ids=selected_turn_ids,
            reason=gate.reason,
        )
        return self._build_selected(
            session_id=session_id,
            user_id=user_id,
            current_message=current_message,
            raw_history=raw_history,
            selected_history=selected_history,
            available_tools=available_tools,
            selected_tools=available_tools or [],
            decision=decision,
            started_at=started_at,
        )


class TaskScopedPolicy(ContextPolicy):
    name = "task_scoped"

    def __init__(self, max_task_turns: int = 6):
        self.max_task_turns = max_task_turns
        self.need_gate = RuleBasedNeedGate()
        self.boundary_detector = RuleBasedBoundaryDetector()
        self.retriever = ScopedRetriever(max_turns=max_task_turns)
        self.evidence_validator = EvidenceValidator()
        self.tool_filter = RuleBasedToolFilter()
        self.assembler = PromptAssembler()

    def select(
        self,
        session_id: str,
        user_id: str,
        current_message: str,
        raw_history: list[dict[str, Any]],
        available_tools: list[Any] | None = None,
    ) -> SelectedContext:
        started_at = perf_counter()
        gate = self.need_gate.decide(current_message)
        boundary_decision = self.boundary_detector.decide(raw_history, gate)
        candidates = self.retriever.retrieve(raw_history, boundary_decision.task_id, gate.need_type)
        selected_history = self.evidence_validator.validate(current_message, candidates, gate.need_type)
        selected_turn_ids = [
            _message_id(message, raw_history.index(message)) for message in selected_history if message in raw_history
        ]
        decision = ContextDecision(
            self_sufficient=gate.self_sufficient,
            need_type=gate.need_type,
            boundary=boundary_decision.boundary,
            task_id=boundary_decision.task_id,
            confidence=min(gate.confidence, boundary_decision.confidence),
            selected_turn_ids=selected_turn_ids,
            reason=f"{gate.reason} {boundary_decision.reason}",
        )
        selected_tools = self.tool_filter.filter(current_message, available_tools, gate.need_type)
        messages = self.assembler.assemble_messages(selected_history)
        return self._build_selected(
            session_id=session_id,
            user_id=user_id,
            current_message=current_message,
            raw_history=raw_history,
            selected_history=messages,
            available_tools=available_tools,
            selected_tools=selected_tools,
            decision=decision,
            started_at=started_at,
            system_addendum=self.assembler.system_addendum(self.name),
        )

class TaskScopedToolFilterPolicy(TaskScopedPolicy):
    name = "task_scoped_tool_filter"


class OracleBoundaryPolicy(ContextPolicy):
    name = "oracle_boundary"

    def __init__(self, oracle_task_id: str | None = None, max_turns: int = 6):
        self.oracle_task_id = oracle_task_id
        self.max_turns = max_turns

    def select(
        self,
        session_id: str,
        user_id: str,
        current_message: str,
        raw_history: list[dict[str, Any]],
        available_tools: list[Any] | None = None,
    ) -> SelectedContext:
        started_at = perf_counter()
        task_id = self.oracle_task_id
        if task_id is None:
            task_id = self._infer_oracle_task_id(current_message, raw_history)
        selected_history = [message for message in raw_history if task_id and message.get("task_id") == task_id]
        selected_history = selected_history[-self.max_turns :]
        selected_turn_ids = [
            _message_id(message, raw_history.index(message)) for message in selected_history if message in raw_history
        ]
        decision = ContextDecision(
            self_sufficient=not selected_history,
            need_type="task_local" if selected_history else "no_context",
            boundary="continue_task" if selected_history else "new_task",
            task_id=task_id if selected_history else None,
            confidence=1.0,
            selected_turn_ids=selected_turn_ids,
            reason="Oracle policy: select turns with the provided or inferred task id.",
        )
        return self._build_selected(
            session_id=session_id,
            user_id=user_id,
            current_message=current_message,
            raw_history=raw_history,
            selected_history=selected_history,
            available_tools=available_tools,
            selected_tools=available_tools or [],
            decision=decision,
            started_at=started_at,
        )

    def _infer_oracle_task_id(self, current_message: str, raw_history: list[dict[str, Any]]) -> str | None:
        if not raw_history:
            return None
        import re

        match = re.search(r"\btask_id:([A-Za-z0-9_\-:.]+)", current_message)
        if match:
            return match.group(1)
        return raw_history[-1].get("task_id")
