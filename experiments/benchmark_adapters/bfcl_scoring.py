from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)


def parse_call_string(text: str) -> ParsedCall | None:
    text = text.strip()
    if not text:
        return None
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(node, ast.Call):
        return None
    name = _node_name(node.func)
    if not name:
        return None
    args: dict[str, Any] = {}
    for index, arg in enumerate(node.args):
        args[f"arg{index}"] = _literal(arg)
    for keyword in node.keywords:
        if keyword.arg is not None:
            args[keyword.arg] = _literal(keyword.value)
    return ParsedCall(name=name, args=args)


def parse_model_calls(content: str) -> list[ParsedCall]:
    candidates = []
    text = content.strip()
    try:
        obj = json.loads(text)
        candidates.extend(_calls_from_json(obj))
    except Exception:
        pass
    for match in re.finditer(r"([A-Za-z_][A-Za-z0-9_.]*)\s*\(([^()]*)\)", text):
        call = parse_call_string(match.group(0))
        if call:
            candidates.append(call)
    return candidates


def score_bfcl(content: str, gold: Any) -> dict[str, Any]:
    predicted = parse_model_calls(content)
    expected = expected_calls(gold)
    matched = 0
    wrong_tool = 0
    wrong_arguments = 0
    used_expected = set()
    for pred in predicted:
        candidates = [i for i, exp in enumerate(expected) if exp.name == pred.name and i not in used_expected]
        if not candidates:
            wrong_tool += 1
            continue
        best_index = candidates[0]
        exp = expected[best_index]
        if args_match(pred.args, exp.args):
            matched += 1
            used_expected.add(best_index)
        else:
            wrong_arguments += 1
    return {
        "benchmark_score": bool(expected and matched == len(expected) and len(predicted) == len(expected)),
        "benchmark_scored": bool(expected),
        "score_type": "bfcl_local_ast_approx",
        "expected_call_count": len(expected),
        "predicted_call_count": len(predicted),
        "matched_call_count": matched,
        "wrong_tool_count": wrong_tool,
        "wrong_argument_count": wrong_arguments,
        "expected_calls": [{"name": call.name, "args": call.args} for call in expected],
        "predicted_calls": [{"name": call.name, "args": call.args} for call in predicted],
        "eval_details": [],
    }


def expected_calls(gold: Any) -> list[ParsedCall]:
    calls: list[ParsedCall] = []
    if isinstance(gold, list):
        for item in gold:
            if isinstance(item, dict):
                calls.extend(_calls_from_ground_truth_dict(item))
            elif isinstance(item, list):
                for nested in item:
                    if isinstance(nested, str):
                        parsed = parse_call_string(nested)
                        if parsed:
                            calls.append(parsed)
            elif isinstance(item, str):
                parsed = parse_call_string(item)
                if parsed:
                    calls.append(parsed)
    elif isinstance(gold, dict):
        calls.extend(_calls_from_ground_truth_dict(gold))
    return calls


def args_match(predicted: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key, expected_value in expected.items():
        if key not in predicted:
            return False
        if isinstance(expected_value, list):
            if not any(_value_equal(predicted[key], value) for value in expected_value):
                return False
        elif not _value_equal(predicted[key], expected_value):
            return False
    return True


def _calls_from_ground_truth_dict(item: dict[str, Any]) -> list[ParsedCall]:
    calls = []
    for name, args in item.items():
        calls.append(ParsedCall(name=str(name), args=args if isinstance(args, dict) else {}))
    return calls


def _calls_from_json(obj: Any) -> list[ParsedCall]:
    calls = []
    if isinstance(obj, dict):
        name = obj.get("name") or obj.get("tool") or obj.get("function")
        args = obj.get("arguments") or obj.get("args") or {}
        if isinstance(name, dict):
            args = name.get("arguments") or args
            name = name.get("name")
        if name:
            calls.append(ParsedCall(name=str(name), args=args if isinstance(args, dict) else {}))
        for value in obj.values():
            calls.extend(_calls_from_json(value))
    elif isinstance(obj, list):
        for item in obj:
            calls.extend(_calls_from_json(item))
    return calls


def _node_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _node_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return None


def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        return ast.unparse(node)


def _value_equal(left: Any, right: Any) -> bool:
    if left == right:
        return True
    return str(left) == str(right)
