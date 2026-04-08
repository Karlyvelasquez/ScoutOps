import re


class GuardrailViolationError(ValueError):
    pass


SUSPICIOUS_PATTERNS = [
    r"ignore\s+(all|any|previous)\s+instructions",
    r"system\s+prompt",
    r"developer\s+message",
    r"reveal\s+.*\s+prompt",
    r"\<\s*script",
    r"```",
    r"\$\(.*\)",
    r"\brm\s+-rf\b",
    r"\bcurl\s+http",
    r"\bwget\s+http",
    r"\b(base64|powershell|bash\s+-c)\b",
]


def sanitize_text(value: str) -> str:
    # Remove control characters and collapse excessive whitespace.
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", value)
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def assert_safe_text(value: str) -> None:
    lowered = value.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, lowered):
            raise GuardrailViolationError(
                "Input rejected by security guardrails (possible prompt injection)."
            )
