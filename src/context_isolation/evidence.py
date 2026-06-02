from __future__ import annotations


class EvidenceValidator:
    def validate(self, current_message: str, candidates: list[dict], need_type: str) -> list[dict]:
        if need_type == "no_context":
            return []
        if need_type == "clarification":
            return []
        return list(candidates)
