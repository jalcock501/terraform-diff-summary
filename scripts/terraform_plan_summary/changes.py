"""Terraform resource change classification and filtering."""

from __future__ import annotations

from typing import Any

from terraform_plan_summary.diff import strip_ignored_tags


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
