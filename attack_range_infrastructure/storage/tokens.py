"""Replace `$USER$` and `$PASSWORD$` in template values."""

import re
from typing import Any

_TOKEN = re.compile(r"\$(?:USER|PASSWORD)\$")


def substitute(value: Any, tokens: dict[str, str]) -> Any:
    """Replace config tokens in strings. Inserted values are not scanned again."""
    if isinstance(value, str):
        return _TOKEN.sub(lambda match: tokens[match.group(0)], value)
    if isinstance(value, list):
        return [substitute(item, tokens) for item in value]
    if isinstance(value, dict):
        return {key: substitute(item, tokens) for key, item in value.items()}
    return value


def contains_token(value: Any) -> bool:
    """Return whether a string anywhere in `value` still contains `$USER$` or `$PASSWORD$`."""
    if isinstance(value, str):
        return _TOKEN.search(value) is not None
    if isinstance(value, list):
        return any(contains_token(item) for item in value)
    if isinstance(value, dict):
        return any(contains_token(item) for item in value.values())
    return False
