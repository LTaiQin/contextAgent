from __future__ import annotations

import json
import math
import re
from collections import Counter
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
        if mode == "weighted":
            ranked = self.rank_turns_weighted(sample, session_index)
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
        if mode == "lexical_turn":
            ranked = self.rank_sessions_by_turn_evidence(sample)
            return ranked[:max_sessions]
        if mode == "lexical_adaptive":
            return self.select_adaptive_session_indexes(sample, base_sessions=max_sessions)
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

    def rank_sessions_by_turn_evidence(self, sample: dict[str, Any]) -> list[int]:
        return [index for score, index in self.score_sessions_by_turn_evidence(sample) if score > 0] or list(
            range(min(len(sample.get("haystack_sessions", [])), 1))
        )

    def score_sessions_by_turn_evidence(self, sample: dict[str, Any]) -> list[tuple[float, int]]:
        sessions = sample.get("haystack_sessions", [])
        if not sessions:
            return []
        question_terms = self._query_terms(str(sample.get("question", "")))
        if not question_terms:
            return [(1.0, index) for index in range(min(len(sessions), 1))]
        idf = self._session_idf(sessions)
        scored: list[tuple[float, int]] = []
        for session_index, session in enumerate(sessions):
            turn_scores = [
                self._turn_relevance_score(turn, question_terms, idf) for turn in session
            ]
            positive_scores = [score for score in turn_scores if score > 0]
            if not positive_scores:
                scored.append((0.0, session_index))
                continue
            top_scores = sorted(positive_scores, reverse=True)[:3]
            top_score = top_scores[0]
            mean_top = sum(top_scores) / len(top_scores)
            density = len(positive_scores) / max(1, len(session))
            score = top_score + 0.35 * mean_top + 0.25 * density
            scored.append((score, session_index))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return scored

    def select_adaptive_session_indexes(self, sample: dict[str, Any], base_sessions: int = 3) -> list[int]:
        scored = self.score_sessions_by_turn_evidence(sample)
        ranked = [index for score, index in scored if score > 0]
        if not ranked:
            return list(range(min(len(sample.get("haystack_sessions", [])), 1)))
        budget = self.adaptive_session_budget(sample, scored, base_sessions=base_sessions)
        return ranked[:budget]

    def adaptive_session_budget(
        self,
        sample: dict[str, Any],
        scored: list[tuple[float, int]],
        base_sessions: int = 3,
    ) -> int:
        question = str(sample.get("question", "")).lower()
        question_type = str(sample.get("question_type", ""))
        positive_scores = [score for score, _index in scored if score > 0]
        if not positive_scores:
            return base_sessions
        if question_type == "multi-session" or any(term in question for term in AGGREGATION_MARKERS):
            return max(base_sessions, 6)
        if len(positive_scores) <= base_sessions:
            return len(positive_scores)
        top_score = positive_scores[0]
        kth_score = positive_scores[base_sessions - 1]
        next_score = positive_scores[base_sessions]
        if top_score <= 0:
            return base_sessions
        next_ratio = next_score / top_score
        boundary_gap = (kth_score - next_score) / top_score
        if next_ratio >= 0.78 or boundary_gap <= 0.05:
            return max(base_sessions, 6)
        return base_sessions

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

    def rank_turns_weighted(self, sample: dict[str, Any], session_index: int) -> list[int]:
        sessions = sample.get("haystack_sessions", [])
        if session_index >= len(sessions) or session_index < 0:
            return []
        question_terms = self._query_terms(str(sample.get("question", "")))
        idf = self._session_idf(sessions)
        scored = [
            (self._turn_relevance_score(turn, question_terms, idf), index)
            for index, turn in enumerate(sessions[session_index])
        ]
        scored.sort(key=lambda item: (-item[0], item[1]))
        ranked = [index for score, index in scored if score > 0]
        if ranked:
            return ranked
        return list(range(min(len(sessions[session_index]), 1)))

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

    @classmethod
    def _query_terms(cls, text: str) -> set[str]:
        return cls._terms(text) - STOPWORDS

    @classmethod
    def _session_idf(cls, sessions: list[list[dict[str, Any]]]) -> dict[str, float]:
        document_frequency: Counter[str] = Counter()
        for session in sessions:
            terms = cls._terms(" ".join(str(turn.get("content", "")) for turn in session))
            document_frequency.update(terms)
        session_count = max(1, len(sessions))
        return {
            term: math.log((session_count + 1) / (frequency + 1)) + 1.0
            for term, frequency in document_frequency.items()
        }

    @classmethod
    def _turn_relevance_score(
        cls,
        turn: dict[str, Any],
        question_terms: set[str],
        idf: dict[str, float],
    ) -> float:
        content = str(turn.get("content", ""))
        turn_terms = cls._terms(content)
        overlap = question_terms & turn_terms
        if not overlap:
            return 0.0
        score = sum(idf.get(term, 1.0) for term in overlap)
        score += 0.25 * len(overlap)
        if turn.get("role") == "user":
            score += 0.2
        if any(marker in content.lower() for marker in ANSWER_MARKERS):
            score += 0.4
        return score


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
}

ANSWER_MARKERS = (
    "i ",
    "i'",
    "i've",
    "my ",
    "last ",
    "yesterday",
    "today",
    "ago",
)

AGGREGATION_MARKERS = (
    "how many",
    "how much",
    "how long",
    "total",
    "different",
    "times",
    "days",
    "weeks",
    "months",
    "past two",
    "this year",
)


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
