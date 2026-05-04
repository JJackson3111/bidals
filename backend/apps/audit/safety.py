import json


SENSITIVE_METADATA_KEYWORDS = (
    "authorization",
    "credential",
    "password",
    "refresh",
    "secret",
    "token",
    "api_key",
    "access_key",
)


def sanitize_metadata(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, nested_value in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                sanitized[key_text] = "[REDACTED]"
            else:
                sanitized[key_text] = sanitize_metadata(nested_value)
        return sanitized

    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value]

    return value


def metadata_summary(metadata, *, max_length: int = 1200) -> str:
    payload = json.dumps(sanitize_metadata(metadata or {}), default=str, ensure_ascii=True, sort_keys=True)
    if len(payload) <= max_length:
        return payload
    return f"{payload[: max_length - 3]}..."


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(keyword in lowered for keyword in SENSITIVE_METADATA_KEYWORDS)
