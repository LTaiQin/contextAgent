from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from context_isolation import (  # noqa: E402
    FullSessionPolicy,
    NeedGatedPolicy,
    RecentNPolicy,
    RetrievalOnlyPolicy,
    TaskScopedPolicy,
    TaskScopedToolFilterPolicy,
)


def make_policy(name: str):
    if name == "full_session":
        return FullSessionPolicy()
    if name == "recent_n":
        return RecentNPolicy(n=4)
    if name == "retrieval_only":
        return RetrievalOnlyPolicy(top_k=4)
    if name == "need_gated":
        return NeedGatedPolicy(max_turns=6)
    if name == "task_scoped":
        return TaskScopedPolicy(max_task_turns=6)
    if name == "task_scoped_tool_filter":
        return TaskScopedToolFilterPolicy(max_task_turns=6)
    raise ValueError(f"Unsupported policy: {name}")
