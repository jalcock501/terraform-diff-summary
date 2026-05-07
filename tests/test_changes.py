from __future__ import annotations

from terraform_plan_summary.changes import is_ignored_tag_only, is_version_tag_only


def test_version_tag_only_update_is_filtered(resource_change) -> None:
    change = resource_change(
        "aws_s3_bucket.example",
        "aws_s3_bucket",
        ["update"],
        {"tags": {"Name": "example", "Version": "old"}},
        {"tags": {"Name": "example", "Version": "new"}},
    )

    assert is_version_tag_only(change, "Version")


def test_multiple_ignored_tag_only_update_is_filtered(resource_change) -> None:
    change = resource_change(
        "aws_s3_bucket.example",
        "aws_s3_bucket",
        ["update"],
        {"tags": {"Name": "example", "Build": "1", "Version": "old"}},
        {"tags": {"Name": "example", "Build": "2", "Version": "new"}},
    )

    assert is_ignored_tag_only(change, {"Build", "Version"})


def test_update_with_other_changes_is_not_version_tag_only(resource_change) -> None:
    change = resource_change(
        "aws_s3_bucket.example",
        "aws_s3_bucket",
        ["update"],
        {"bucket": "old", "tags": {"Name": "example", "Version": "old"}},
        {"bucket": "new", "tags": {"Name": "example", "Version": "new"}},
    )

    assert not is_version_tag_only(change, "Version")
