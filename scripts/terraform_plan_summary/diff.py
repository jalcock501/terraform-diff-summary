"""Diff and field-path helpers for Terraform JSON values."""

from __future__ import annotations

from typing import Any

PathParts = tuple[str, ...]
MISSING = object()


def strip_ignored_tags(value: Any, ignored_tag_names: set[str]) -> Any:
    """Return value with ignored tag keys removed from tag maps."""
    if isinstance(value, dict):
        stripped: dict[str, Any] = {}
        for key, child in value.items():
            if key in {"tags", "tags_all"} and isinstance(child, dict):
                stripped[key] = {
                    tag_key: tag_value
                    for tag_key, tag_value in child.items()
                    if tag_key not in ignored_tag_names
                }
            else:
                stripped[key] = strip_ignored_tags(child, ignored_tag_names)
        return stripped

    if isinstance(value, list):
        return [strip_ignored_tags(item, ignored_tag_names) for item in value]

    return value


def strip_version_tag(value: Any, version_tag_name: str) -> Any:
    """Return value with the configured version tag removed from tag maps."""
    return strip_ignored_tags(value, {version_tag_name})


def leaf_paths(value: Any, prefix: PathParts = ()) -> set[PathParts]:
    """Return Terraform-style field paths for scalar leaves in value."""
    if isinstance(value, dict):
        paths: set[PathParts] = set()
        for key, child in value.items():
            paths.update(leaf_paths(child, (*prefix, str(key))))
        return paths or {prefix}

    if isinstance(value, list):
        paths = set()
        for index, child in enumerate(value):
            paths.update(leaf_paths(child, (*prefix, str(index))))
        return paths or {prefix}

    return {prefix}


def value_at_path(value: Any, path: PathParts) -> Any:
    """Look up a tuple path in nested Terraform JSON data."""
    current = value
    for part in path:
        if isinstance(current, dict):
            current = current.get(part, MISSING)
            if current is MISSING:
                return MISSING
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (IndexError, ValueError):
                return MISSING
        else:
            return MISSING
    return current


def format_path(path: PathParts) -> str:
    return ".".join(path) if path else "value"


def changed_field_paths(before: Any, after: Any) -> list[str]:
    """Return sorted field paths whose before/after values differ."""
    paths = leaf_paths(before) | leaf_paths(after)
    if any(path for path in paths):
        paths.discard(())
    paths = {
        path
        for path in paths
        if not any(other != path and other[: len(path)] == path for other in paths)
    }

    changed = [
        format_path(path)
        for path in sorted(paths)
        if value_at_path(before, path) != value_at_path(after, path)
    ]
    return changed


def changed_paths(before: Any, after: Any, max_changed_fields: int) -> str:
    """Format changed paths with a per-resource cap."""
    changed = changed_field_paths(before, after)
    if not changed:
        return "n/a"

    if len(changed) > max_changed_fields:
        changed = [*changed[:max_changed_fields], "..."]

    return ", ".join(changed)


def display_changed_paths(
    before: Any,
    after: Any,
    ignored_tag_names: set[str],
    max_changed_fields: int,
    *,
    hide_ignored_tags: bool,
) -> str:
    if not hide_ignored_tags:
        return changed_paths(before, after, max_changed_fields)

    stripped_before = strip_ignored_tags(before, ignored_tag_names)
    stripped_after = strip_ignored_tags(after, ignored_tag_names)
    return changed_paths(stripped_before, stripped_after, max_changed_fields)
