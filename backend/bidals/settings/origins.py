from __future__ import annotations

from collections.abc import Iterable


def comma_separated_urls(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        raw_items = value.split(",")
    else:
        raw_items = []
        for item in value:
            raw_items.extend(str(item).split(","))

    return [item.strip() for item in raw_items if item.strip()]


def configured_origins(env, names: Iterable[str], *, default: Iterable[str] = ()) -> list[str]:
    origins: list[str] = []
    for name in names:
        origins.extend(comma_separated_urls(env(name, default="")))

    if not origins:
        origins.extend(comma_separated_urls(default))

    return list(dict.fromkeys(origins))
