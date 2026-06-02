from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


NeedType = Literal[
    "no_context",
    "task_local",
    "related_summary",
    "global_profile",
    "project_memory",
    "tool_state",
    "clarification",
]

TaskBoundary = Literal["new_task", "continue_task", "related_task", "ambiguous"]
TaskStatus = Literal["active", "suspended", "completed", "archived"]
RiskLevel = Literal["low", "medium", "high"]


@dataclass
class ChatTurn:
    turn_id: str
    session_id: str
    role: str
    content: str
    timestamp: str
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskContext:
    task_id: str
    session_id: str
    status: TaskStatus
    title: str
    domain: str | None = None
    summary: str = ""
    turn_ids: list[str] = field(default_factory=list)
    local_facts: dict[str, Any] = field(default_factory=dict)
    tool_state: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    skills_used: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ContextDecision:
    self_sufficient: bool
    need_type: NeedType
    boundary: TaskBoundary
    task_id: str | None
    confidence: float
    selected_turn_ids: list[str] = field(default_factory=list)
    selected_memory_ids: list[str] = field(default_factory=list)
    selected_tools: list[str] = field(default_factory=list)
    suppressed_tools: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class GateDecision:
    self_sufficient: bool
    needs_history: bool
    need_type: NeedType
    confidence: float
    reason: str
    missing_info: list[str] = field(default_factory=list)
    risk_if_using_history: RiskLevel = "medium"


@dataclass
class BoundaryDecision:
    boundary: TaskBoundary
    task_id: str | None
    confidence: float
    reason: str
    candidate_task_ids: list[str] = field(default_factory=list)


@dataclass
class SelectedContext:
    system_addendum: str
    messages: list[dict[str, Any]]
    memories: list[dict[str, Any]]
    tools: list[Any]
    trace: dict[str, Any]
    decision: ContextDecision
