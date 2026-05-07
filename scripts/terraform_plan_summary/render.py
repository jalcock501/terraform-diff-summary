"""Markdown rendering for Terraform plan summaries."""

from __future__ import annotations

from typing import Any

from terraform_plan_summary.changes import action_group, partition_changes
from terraform_plan_summary.diff import display_changed_paths

GROUP_ORDER = ("replace", "delete", "create", "update", "other")
GROUP_TITLES = {
    "replace": "Replacements",
    "delete": "Deletes",
    "create": "Creates",
    "update": "Updates",
    "other": "Other changes",
}


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|")


def markdown_row(values: list[str]) -> str:
    escaped = [markdown_escape(value) for value in values]
    return "| " + " | ".join(escaped) + " |"


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
    if ignored_tag_names is None:
        ignored_tag_names = [version_tag_name]
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
        markdown_row(["Field", "Count"]),
        markdown_row(["---", "---:"]),
        markdown_row(["Resource changes", str(len(changes))]),
        markdown_row(
            ["Filtered tag-only changes " f"({ignored_tag_label})", str(len(filtered))]
        ),
        markdown_row(["Changes shown below", str(len(visible))]),
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
