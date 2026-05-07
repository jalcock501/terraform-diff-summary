"""Render a compact Terraform plan summary for GitHub Actions."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PathParts = tuple[str, ...]
MISSING = object()
GROUP_ORDER = ("replace", "delete", "create", "update", "other")
GROUP_TITLES = {
    "replace": "Replacements",
    "delete": "Deletes",
    "create": "Creates",
    "update": "Updates",
    "other": "Other changes",
}


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def env_bool(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None or raw_value == "":
        return default
    return raw_value.lower() in {"1", "true", "yes", "y", "on"}


def ignored_tag_names_from_env() -> list[str]:
    ignored_tag_names = split_csv(os.environ.get("IGNORED_TAG_NAMES"))
    if ignored_tag_names:
        return ignored_tag_names
    return split_csv(os.environ.get("VERSION_TAG_NAME")) or ["Version"]


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


def change_actions(change: dict[str, Any]) -> list[str]:
    actions = change.get("change", {}).get("actions", [])
    return [str(action) for action in actions]


def is_replace(change: dict[str, Any]) -> bool:
    return set(change_actions(change)) == {"delete", "create"}


def is_destroy(change: dict[str, Any]) -> bool:
    return change_actions(change) == ["delete"]


def action_group(change: dict[str, Any]) -> str:
    actions = change_actions(change)
    if set(actions) == {"delete", "create"}:
        return "replace"
    if actions == ["delete"]:
        return "delete"
    if actions == ["create"]:
        return "create"
    if actions == ["update"]:
        return "update"
    return "other"


def is_actionable(change: dict[str, Any]) -> bool:
    return change.get("change", {}).get("actions") != ["no-op"]


def is_version_tag_only(change: dict[str, Any], version_tag_name: str) -> bool:
    """Return true when an update changes only the configured tag fields."""
    return is_ignored_tag_only(change, {version_tag_name})


def is_ignored_tag_only(change: dict[str, Any], ignored_tag_names: set[str]) -> bool:
    """Return true when an update changes only ignored tag fields."""
    change_body = change.get("change", {})
    if change_body.get("actions") != ["update"]:
        return False

    before = change_body.get("before")
    after = change_body.get("after")
    if before == after:
        return False

    return strip_ignored_tags(before, ignored_tag_names) == strip_ignored_tags(
        after, ignored_tag_names
    )


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|")


def markdown_row(values: list[str]) -> str:
    escaped = [markdown_escape(value) for value in values]
    return "| " + " | ".join(escaped) + " |"


def partition_changes(
    plan: dict[str, Any],
    ignored_tag_names: set[str],
    *,
    filter_tag_only_changes: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    changes = [
        change
        for change in plan.get("resource_changes", [])
        if is_actionable(change)
    ]
    filtered = [
        change
        for change in changes
        if filter_tag_only_changes and is_ignored_tag_only(change, ignored_tag_names)
    ]
    visible = [
        change
        for change in changes
        if not (filter_tag_only_changes and is_ignored_tag_only(change, ignored_tag_names))
    ]
    return changes, filtered, visible


def render_summary(
    plan: dict[str, Any],
    version_tag_name: str = "Version",
    max_changed_fields: int = 8,
    *,
    ignored_tag_names: list[str] | None = None,
    filter_tag_only_changes: bool = True,
    summary_title: str = "Terraform plan summary",
) -> str:
    """Render the Terraform summary Markdown."""
    ignored_tag_names = ignored_tag_names or [version_tag_name]
    ignored_tag_name_set = set(ignored_tag_names)
    changes, filtered, visible = partition_changes(
        plan,
        ignored_tag_name_set,
        filter_tag_only_changes=filter_tag_only_changes,
    )
    ignored_tag_label = ", ".join(ignored_tag_names)

    lines = [
        f"### {summary_title}",
        "",
        "| Field | Count |",
        "|---|---:|",
        f"| Resource changes | {len(changes)} |",
        f"| Filtered tag-only changes ({ignored_tag_label}) | {len(filtered)} |",
        f"| Changes shown below | {len(visible)} |",
        "",
    ]

    if not visible:
        lines.append(
            "No material resource changes after applying the configured filters."
        )
        return "\n".join(lines) + "\n"

    grouped_changes = {
        group: [change for change in visible if action_group(change) == group]
        for group in GROUP_ORDER
    }

    for group in GROUP_ORDER:
        group_changes = grouped_changes[group]
        if not group_changes:
            continue

        lines.extend(
            [
                f"#### {GROUP_TITLES[group]} ({len(group_changes)})",
                "",
                markdown_row(["Address", "Action", "Type", "Changed fields"]),
                markdown_row(["---", "---", "---", "---"]),
            ]
        )

        for change in group_changes:
            change_body = change.get("change", {})
            before = change_body.get("before")
            after = change_body.get("after")
            changed_fields = display_changed_paths(
                before,
                after,
                ignored_tag_name_set,
                max_changed_fields,
                hide_ignored_tags=filter_tag_only_changes,
            )

            lines.append(
                markdown_row(
                    [
                        f"`{change.get('address', 'unknown')}`",
                        f"`{','.join(change_body.get('actions', []))}`",
                        f"`{change.get('type', 'unknown')}`",
                        f"`{changed_fields}`",
                    ]
                )
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def visible_changes(
    plan: dict[str, Any],
    ignored_tag_names: list[str],
    *,
    filter_tag_only_changes: bool,
) -> list[dict[str, Any]]:
    _, _, visible = partition_changes(
        plan,
        set(ignored_tag_names),
        filter_tag_only_changes=filter_tag_only_changes,
    )
    return visible


def count_label(count: int, singular: str, plural: str) -> str:
    label = singular if count == 1 else plural
    return f"{count} {label}"


def failure_message(
    changes: list[dict[str, Any]],
    *,
    fail_on_destroy: bool,
    fail_on_replace: bool,
) -> str | None:
    destroy_count = sum(1 for change in changes if is_destroy(change))
    replace_count = sum(1 for change in changes if is_replace(change))
    failures = []

    if fail_on_destroy and destroy_count:
        failures.append(count_label(destroy_count, "destroy change", "destroy changes"))

    if fail_on_replace and replace_count:
        failures.append(
            count_label(replace_count, "replacement change", "replacement changes")
        )

    if failures:
        return "Terraform plan contains " + " and ".join(failures) + "."

    return None


def env_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None or raw_value == "":
        return default
    return int(raw_value)


def append_summary(path: Path, summary: str) -> None:
    with path.open("a", encoding="utf-8") as summary_file:
        summary_file.write(summary)


def main() -> None:
    plan_json_path = Path(os.environ["PLAN_JSON_PATH"])
    ignored_tag_names = ignored_tag_names_from_env()
    filter_tag_only_changes = env_bool("FILTER_TAG_ONLY_CHANGES", True)
    max_changed_fields = env_int("MAX_CHANGED_FIELDS", 8)
    summary_title = os.environ.get("SUMMARY_TITLE") or "Terraform plan summary"
    fail_on_destroy = env_bool("FAIL_ON_DESTROY", False)
    fail_on_replace = env_bool("FAIL_ON_REPLACE", False)

    plan = json.loads(plan_json_path.read_text(encoding="utf-8"))
    summary = render_summary(
        plan,
        max_changed_fields=max_changed_fields,
        ignored_tag_names=ignored_tag_names,
        filter_tag_only_changes=filter_tag_only_changes,
        summary_title=summary_title,
    )

    summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"])
    append_summary(summary_path, summary)

    summary_output_path = os.environ.get("SUMMARY_OUTPUT_PATH")
    if summary_output_path:
        append_summary(Path(summary_output_path), summary)

    shown_changes = visible_changes(
        plan,
        ignored_tag_names,
        filter_tag_only_changes=filter_tag_only_changes,
    )
    message = failure_message(
        shown_changes,
        fail_on_destroy=fail_on_destroy,
        fail_on_replace=fail_on_replace,
    )
    if message:
        sys.exit(message)


if __name__ == "__main__":
    main()
