"""Compatibility entrypoint for the Terraform diff summary action."""

from __future__ import annotations

from terraform_plan_summary.changes import (
    is_ignored_tag_only,
    is_version_tag_only,
    visible_changes,
)
from terraform_plan_summary.cli import main
from terraform_plan_summary.diff import (
    changed_paths,
    strip_ignored_tags,
    strip_version_tag,
)
from terraform_plan_summary.policy import failure_message
from terraform_plan_summary.render import render_summary

__all__ = [
    "changed_paths",
    "failure_message",
    "is_ignored_tag_only",
    "is_version_tag_only",
    "main",
    "render_summary",
    "strip_ignored_tags",
    "strip_version_tag",
    "visible_changes",
]


if __name__ == "__main__":
    main()
