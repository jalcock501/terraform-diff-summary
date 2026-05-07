"""Failure policy checks for visible Terraform changes."""

from __future__ import annotations

from typing import Any

from terraform_plan_summary.changes import is_destroy, is_replace


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
