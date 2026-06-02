from __future__ import annotations

import json
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
