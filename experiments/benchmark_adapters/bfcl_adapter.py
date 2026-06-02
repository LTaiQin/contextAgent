from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import TaskUnit


PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
BFCL_DATA_DIR = PROJECT_ROOT / "data" / "bfcl"


class BFCLAdapter:
    name = "bfcl"

    def __init__(self, data_dir: Path = BFCL_DATA_DIR):
        self.data_dir = data_dir
        self._answer_cache: dict[str, dict[str, Any]] = {}
        self._function_cache: dict[str, dict[str, Any]] = {}

    def load_samples(self, category: str = "simple", limit: int | None = None) -> list[dict[str, Any]]:
        path = self._category_path(category)
        if not path.exists():
            raise FileNotFoundError(
                f"Missing BFCL data file: {path}. Download the public BFCL data first."
            )
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return rows[:limit] if limit else rows

    def build_task_unit(self, sample: dict[str, Any]) -> TaskUnit:
        messages = self.flatten_question(sample.get("question", []))
        query = self.messages_to_query(messages)
        functions = sample.get("function") or self.functions_from_path(sample.get("path", []))
        tools = [self.to_openai_tool_schema(function) for function in functions]
        gold = sample.get("ground_truth") or sample.get("answer")
        if gold is None:
            gold = self.lookup_answer(sample.get("id"))
        return TaskUnit(
            task_uid=f"bfcl:{sample.get('id')}",
            source_benchmark="BFCL",
            domain="tool_calling",
            task_type="function_calling",
            query=query,
            system_text="Return the correct tool call for the current user request.",
            gold=gold or {},
            scorer="bfcl_official_pending",
            tools=tools,
            metadata={
                "bfcl_id": sample.get("id"),
                "turn_count": len(sample.get("question", [])),
                "tool_count": len(tools),
            },
        )

    def build_session(self, category: str = "simple", limit: int = 5) -> list[TaskUnit]:
        return [self.build_task_unit(sample) for sample in self.load_samples(category=category, limit=limit)]

    def _category_path(self, category: str) -> Path:
        candidates = {
            "simple": self.data_dir / "BFCL_v3_simple.json",
            "multi_turn_base": self.data_dir / "BFCL_v3_multi_turn_base.json",
        }
        if category in candidates:
            return candidates[category]
        return self.data_dir / f"BFCL_v3_{category}.json"

    def _answer_path(self, category: str) -> Path:
        return self.data_dir / "possible_answer" / f"BFCL_v3_{category}.json"

    def load_answers(self, category: str) -> dict[str, Any]:
        if category in self._answer_cache:
            return self._answer_cache[category]
        path = self._answer_path(category)
        if not path.exists():
            self._answer_cache[category] = {}
            return {}
        answers = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            answers[str(row.get("id"))] = row.get("ground_truth")
        self._answer_cache[category] = answers
        return answers

    def lookup_answer(self, sample_id: str | None) -> Any:
        if not sample_id:
            return None
        for category in ["simple", "multi_turn_base"]:
            answers = self.load_answers(category)
            if sample_id in answers:
                return answers[sample_id]
        return None

    def load_function_docs(self) -> dict[str, dict[str, Any]]:
        if self._function_cache:
            return self._function_cache
        doc_dir = self.data_dir / "multi_turn_func_doc"
        functions = {}
        if not doc_dir.exists():
            self._function_cache = functions
            return functions
        for path in doc_dir.glob("*.json"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                name = row.get("name")
                if name:
                    functions[str(name)] = row
        self._function_cache = functions
        return functions

    def functions_from_path(self, path_items: list[str]) -> list[dict[str, Any]]:
        docs = self.load_function_docs()
        functions = []
        seen = set()
        for item in path_items or []:
            name = str(item).split(".")[-1]
            function = docs.get(name)
            if function and name not in seen:
                functions.append(function)
                seen.add(name)
        return functions

    @staticmethod
    def flatten_question(question: Any) -> list[dict[str, str]]:
        if not isinstance(question, list):
            return []
        messages: list[dict[str, str]] = []
        for turn in question:
            if isinstance(turn, list):
                for message in turn:
                    if isinstance(message, dict):
                        messages.append(
                            {
                                "role": str(message.get("role", "user")),
                                "content": str(message.get("content", "")),
                            }
                        )
            elif isinstance(turn, dict):
                messages.append(
                    {
                        "role": str(turn.get("role", "user")),
                        "content": str(turn.get("content", "")),
                    }
                )
        return messages

    @staticmethod
    def messages_to_query(messages: list[dict[str, str]]) -> str:
        parts = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            parts.append(f"{role.upper()}: {content}")
        return "\n".join(parts)

    @staticmethod
    def to_openai_tool_schema(function: dict[str, Any]) -> dict[str, Any]:
        parameters = function.get("parameters") or {}
        if parameters.get("type") == "dict":
            parameters = dict(parameters)
            parameters["type"] = "object"
        return {
            "type": "function",
            "function": {
                "name": function.get("name"),
                "description": function.get("description", ""),
                "parameters": parameters,
            },
        }
