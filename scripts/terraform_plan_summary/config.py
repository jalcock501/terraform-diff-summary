"""Environment parsing for the Terraform diff summary action."""

from __future__ import annotations

import os


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def env_bool(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None or raw_value == "":
        return default
    return raw_value.lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None or raw_value == "":
        return default
    return int(raw_value)


def ignored_tag_names_from_env() -> list[str]:
    ignored_tag_names = split_csv(os.environ.get("IGNORED_TAG_NAMES"))
    if ignored_tag_names:
        return ignored_tag_names
    return split_csv(os.environ.get("VERSION_TAG_NAME")) or ["Version"]
