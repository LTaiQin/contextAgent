from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .core import TaskUnit


PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
LONGMEMEVAL_DATA_DIR = PROJECT_ROOT / "data" / "longmemeval"


class LongMemEvalAdapter:
    name = "longmemeval"

    def __init__(self, data_dir: Path = LONGMEMEVAL_DATA_DIR):
        self.data_dir = data_dir

    def load_samples(self, split: str = "s_cleaned", limit: int | None = None) -> list[dict[str, Any]]:
        path = self._split_path(split)
        if not path.exists():
            raise FileNotFoundError(f"Missing LongMemEval data file: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return data[:limit] if limit else data

    def build_task_unit(self, sample: dict[str, Any]) -> TaskUnit:
        query = self.build_query(sample)
        return TaskUnit(
            task_uid=f"longmemeval:{sample.get('question_id')}",
            source_benchmark="LongMemEval",
            domain="memory",
            task_type="memory_qa",
            query=query,
            system_text="Answer the question using only the relevant conversation history.",
            gold=sample.get("answer"),
            scorer="longmemeval_string_contains",
            metadata={
                "question_id": sample.get("question_id"),
                "question_type": sample.get("question_type"),
                "question_date": sample.get("question_date"),
                "answer_session_ids": sample.get("answer_session_ids", []),
                "haystack_session_count": len(sample.get("haystack_sessions", [])),
            },
        )

    def build_session(self, split: str = "s_cleaned", limit: int = 5) -> list[TaskUnit]:
        return [self.build_task_unit(sample) for sample in self.load_samples(split=split, limit=limit)]

    def build_compact_context(
        self,
        sample: dict[str, Any],
        mode: str = "oracle",
        max_sessions: int = 3,
        max_turns_per_session: int = 4,
        turn_mode: str = "first_n",
    ) -> str:
        sessions = sample.get("haystack_sessions", [])
        session_ids = sample.get("haystack_session_ids", [])
        selected_indexes = self.select_session_indexes(sample, mode=mode, max_sessions=max_sessions)
        parts = [f"LongMemEval mode={mode}", "Conversation evidence:"]
        for index in selected_indexes:
            session_id = session_ids[index] if index < len(session_ids) else f"session_{index}"
            parts.append(f"\n[Session {index + 1}: {session_id}]")
            turn_indexes = self.select_turn_indexes_in_session(
                sample,
                session_index=index,
                max_turns=max_turns_per_session,
                mode=turn_mode,
            )
            for turn_index in turn_indexes:
                turn = sessions[index][turn_index]
                role = turn.get("role", "user")
                content = turn.get("content", "")
                parts.append(f"{role}: {content}")
        parts.append("\nQuestion:")
        parts.append(str(sample.get("question", "")))
        return "\n".join(parts)

    def select_turn_indexes_in_session(
        self,
        sample: dict[str, Any],
        session_index: int,
        max_turns: int = 4,
        mode: str = "first_n",
    ) -> list[int]:
        sessions = sample.get("haystack_sessions", [])
        if session_index >= len(sessions) or session_index < 0:
            return []
        turns = sessions[session_index]
        if not turns:
            return []
        if mode == "full":
            return list(range(len(turns)))
        if mode == "last_n":
            return list(range(max(0, len(turns) - max_turns), len(turns)))
        if mode == "ranked":
            ranked = self.rank_turns(sample, session_index)
            if not ranked:
                return list(range(min(len(turns), max_turns)))
            ranked = ranked[:max_turns]
            return sorted(ranked)
        return list(range(min(len(turns), max_turns)))

    def select_session_indexes(
        self,
        sample: dict[str, Any],
        mode: str = "oracle",
        max_sessions: int = 3,
    ) -> list[int]:
        sessions = sample.get("haystack_sessions", [])
        if not sessions:
            return []
        if mode == "oracle":
            answer_ids = [str(item) for item in sample.get("answer_session_ids", [])]
            session_ids = [str(item) for item in sample.get("haystack_session_ids", [])]
            selected = [index for index, session_id in enumerate(session_ids) if session_id in answer_ids]
            if selected:
                return selected[:max_sessions]
        ranked = self.rank_sessions(sample)
        return ranked[:max_sessions]

    def rank_sessions(self, sample: dict[str, Any]) -> list[int]:
        sessions = sample.get("haystack_sessions", [])
        if not sessions:
            return []
        query_terms = self._terms(str(sample.get("question", "")))
        scored: list[tuple[int, int]] = []
        for index, session in enumerate(sessions):
            text = " ".join(str(turn.get("content", "")) for turn in session)
            score = len(query_terms & self._terms(text))
            scored.append((score, index))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [index for score, index in scored if score > 0] or list(range(min(len(sessions), 1)))

    def rank_turns(self, sample: dict[str, Any], session_index: int) -> list[int]:
        sessions = sample.get("haystack_sessions", [])
        if session_index >= len(sessions) or session_index < 0:
            return []
        question_terms = self._terms(str(sample.get("question", "")))
        turns = sessions[session_index]
        scored: list[tuple[int, int]] = []
        for index, turn in enumerate(turns):
            content = str(turn.get("content", ""))
            turn_terms = self._terms(content)
            score = len(question_terms & turn_terms)
            if score:
                score += 1 if turn.get("role") == "assistant" else 0
            scored.append((score, index))
        scored.sort(key=lambda item: (-item[0], item[1]))
        ranked = [index for score, index in scored if score > 0]
        if ranked:
            return ranked
        return list(range(min(len(turns), 1)))

    def _split_path(self, split: str) -> Path:
        candidates = {
            "s_cleaned": self.data_dir / "longmemeval_s_cleaned.json",
            "oracle": self.data_dir / "longmemeval_oracle.json",
        }
        if split in candidates:
            return candidates[split]
        return self.data_dir / f"{split}.json"

    @staticmethod
    def build_query(sample: dict[str, Any]) -> str:
        sessions = sample.get("haystack_sessions", [])
        dates = sample.get("haystack_dates", [])
        session_ids = sample.get("haystack_session_ids", [])
        parts = ["Conversation history:"]
        for index, session in enumerate(sessions):
            date = dates[index] if index < len(dates) else ""
            session_id = session_ids[index] if index < len(session_ids) else f"session_{index}"
            parts.append(f"\n[Session {index + 1}: {session_id} | {date}]")
            for message in session:
                role = message.get("role", "user")
                content = message.get("content", "")
                parts.append(f"{role}: {content}")
        parts.append("\nQuestion:")
        parts.append(str(sample.get("question", "")))
        return "\n".join(parts)

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {token.lower() for token in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text)}


def score_longmemeval_string(content: str, gold: Any) -> dict[str, Any]:
    expected = str(gold or "").strip()
    prediction = str(content or "").strip()
    expected_norm = _normalize(expected)
    prediction_norm = _normalize(prediction)
    correct = bool(expected_norm) and expected_norm in prediction_norm
    return {
        "benchmark_score": correct,
        "benchmark_scored": bool(expected_norm),
        "score_type": "longmemeval_string_contains",
        "prediction": prediction,
        "gold": expected,
        "correct_string_contains": correct,
        "eval_details": [],
    }


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())
