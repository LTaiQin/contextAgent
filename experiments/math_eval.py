import re


def last_boxed(text: str) -> str | None:
    marker = "\\boxed{"
    start = str(text).rfind(marker)
    if start == -1:
        return None
    i = start + len(marker)
    depth = 1
    chars = []
    text = str(text)
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
            chars.append(ch)
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(chars).strip()
            chars.append(ch)
        else:
            chars.append(ch)
        i += 1
    return None


def normalize_answer(text: str | None) -> str:
    if text is None:
        return ""
    value = str(text).strip()
    value = re.sub(r"\\frac([0-9])([0-9])", r"\\frac{\1}{\2}", value)
    replacements = {
        "\\left": "",
        "\\right": "",
        "\\dfrac": "\\frac",
        "\\tfrac": "\\frac",
        "\\,": "",
        "\\!": "",
        " ": "",
        "\n": "",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value.strip(".")


def extract_prediction(text: str) -> str:
    boxed = last_boxed(text)
    if boxed:
        return boxed
    patterns = [
        r"(?:final answer|answer|答案)\s*(?:is|=|:|：)\s*([^\n]+)",
        r"\\boxed\{([^}]+)\}",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            return matches[-1].strip()
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    return lines[-1] if lines else ""


def score_prediction(prediction: str, gold: str) -> dict[str, bool]:
    return {
        "correct_raw": bool(gold) and str(prediction).strip() == str(gold).strip(),
        "correct_normalized": bool(gold) and normalize_answer(prediction) == normalize_answer(gold),
    }
