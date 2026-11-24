"""Cloud resource names: `<name>-<identity>-<user name>`."""

from typing import Optional


def resource_name(name: str, identity: str, user_name: str, *, limit: Optional[int] = None) -> str:
    """`<name>-<identity>-<user name>`. A short limit keeps `identity` and then drops the user name."""
    full = f"{name}-{identity}-{user_name}"
    if limit is None or len(full) <= limit:
        return full

    with_user = f"-{identity}-{user_name}"
    if limit > len(with_user):
        head = name[: limit - len(with_user)].rstrip("-")
        if head:
            return f"{head}{with_user}"

    with_prefix = f"-{identity}"
    head = name[: limit - len(with_prefix)].rstrip("-")
    if head and limit >= len(with_prefix) + 1:
        return f"{head}{with_prefix}"
    raise ValueError(f"cannot fit resource name '{name}' into {limit} characters")
