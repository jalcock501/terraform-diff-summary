"""Render a compact Terraform plan summary for GitHub Actions."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PathParts = tuple[str, ...]
MISSING = object()


def strip_version_tag(value: Any, version_tag_name: str) -> Any:
    """Return value with the configured version tag removed from tag maps."""
    if isinstance(value, dict):
        stripped: dict[str, Any] = {}
        for key, child in value.items():
            if key in {"tags", "tags_all"} and isinstance(child, dict):
                stripped[key] = {
                    tag_key: tag_value
                    for tag_key, tag_value in child.items()
                    if tag_key != version_tag_name
                }
            else:
                stripped[key] = strip_version_tag(child, version_tag_name)
        return stripped

    if isinstance(value, list):
        return [strip_version_tag(item, version_tag_name) for item in value]

    return value


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


def is_actionable(change: dict[str, Any]) -> bool:
    return change.get("change", {}).get("actions") != ["no-op"]


def is_version_tag_only(change: dict[str, Any], version_tag_name: str) -> bool:
    """Return true when an update changes only the configured tag fields."""
    change_body = change.get("change", {})
    if change_body.get("actions") != ["update"]:
        return False

    before = change_body.get("before")
    after = change_body.get("after")
    if before == after:
        return False

    return strip_version_tag(before, version_tag_name) == strip_version_tag(
        after, version_tag_name
    )


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|")


def markdown_row(values: list[str]) -> str:
    escaped = [markdown_escape(value) for value in values]
    return "| " + " | ".join(escaped) + " |"


def render_summary(
    plan: dict[str, Any], version_tag_name: str = "Version", max_changed_fields: int = 8
) -> str:
    """Render the Terraform summary Markdown."""
    changes = [
        change
        for change in plan.get("resource_changes", [])
        if is_actionable(change)
    ]
    filtered = [
        change for change in changes if is_version_tag_only(change, version_tag_name)
    ]
    visible = [
        change
        for change in changes
        if not is_version_tag_only(change, version_tag_name)
    ]

    lines = [
        "### Terraform plan summary",
        "",
        "| Field | Count |",
        "|---|---:|",
        f"| Resource changes | {len(changes)} |",
        f"| Filtered {version_tag_name} tag-only changes | {len(filtered)} |",
        f"| Changes shown below | {len(visible)} |",
        "",
    ]

    if not visible:
        lines.append(
            "No material resource changes after filtering "
            f"{version_tag_name} tag-only updates."
        )
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            markdown_row(["Address", "Action", "Type", "Changed fields"]),
            markdown_row(["---", "---", "---", "---"]),
        ]
    )

    for change in visible:
        change_body = change.get("change", {})
        before = strip_version_tag(change_body.get("before"), version_tag_name)
        after = strip_version_tag(change_body.get("after"), version_tag_name)

        lines.append(
            markdown_row(
                [
                    f"`{change.get('address', 'unknown')}`",
                    f"`{','.join(change_body.get('actions', []))}`",
                    f"`{change.get('type', 'unknown')}`",
                    f"`{changed_paths(before, after, max_changed_fields)}`",
                ]
            )
        )

    return "\n".join(lines) + "\n"


def env_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None or raw_value == "":
        return default
    return int(raw_value)


def main() -> None:
    plan_json_path = Path(os.environ["PLAN_JSON_PATH"])
    version_tag_name = os.environ.get("VERSION_TAG_NAME") or "Version"
    max_changed_fields = env_int("MAX_CHANGED_FIELDS", 8)

    plan = json.loads(plan_json_path.read_text(encoding="utf-8"))
    summary = render_summary(plan, version_tag_name, max_changed_fields)

    summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"])
    with summary_path.open("a", encoding="utf-8") as summary_file:
        summary_file.write(summary)


if __name__ == "__main__":
    main()
