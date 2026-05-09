"""Command-line entrypoint for the Terraform diff summary action."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from terraform_plan_summary.changes import visible_changes
from terraform_plan_summary.config import (
    env_bool,
    env_int,
    ignored_tag_names_from_env,
)
from terraform_plan_summary.policy import failure_message
from terraform_plan_summary.pr_comment import (
    DEFAULT_COMMENT_TITLE,
    post_pull_request_comment_from_env,
)
from terraform_plan_summary.render import render_summary


def append_summary(path: Path, summary: str) -> None:
    with path.open("a", encoding="utf-8") as summary_file:
        summary_file.write(summary)


def main() -> None:
    plan_json_path = Path(os.environ["PLAN_JSON_PATH"])
    ignored_tag_names = ignored_tag_names_from_env()
    filter_tag_only_changes = env_bool("FILTER_TAG_ONLY_CHANGES", True)
    max_changed_fields = env_int("MAX_CHANGED_FIELDS", 8)
    if max_changed_fields < 1:
        raise SystemExit("MAX_CHANGED_FIELDS must be greater than or equal to 1")
    summary_title = os.environ.get("SUMMARY_TITLE") or "Terraform plan summary"
    fail_on_destroy = env_bool("FAIL_ON_DESTROY", False)
    fail_on_replace = env_bool("FAIL_ON_REPLACE", False)
    comment_on_pr = env_bool("COMMENT_ON_PR", False)
    comment_title = os.environ.get("COMMENT_TITLE") or DEFAULT_COMMENT_TITLE

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

    if comment_on_pr:
        post_pull_request_comment_from_env(summary, comment_title)

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
