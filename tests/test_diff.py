from __future__ import annotations

from terraform_plan_summary.diff import (
    changed_paths,
    strip_ignored_tags,
    strip_version_tag,
)


def test_strip_version_tag_removes_configured_tag_from_tags_and_tags_all() -> None:
    value = {
        "tags": {"Name": "bucket", "Version": "v1"},
        "tags_all": {"Environment": "dev", "Version": "v1"},
        "nested": [{"tags": {"Version": "v1", "Owner": "team"}}],
    }

    assert strip_version_tag(value, "Version") == {
        "tags": {"Name": "bucket"},
        "tags_all": {"Environment": "dev"},
        "nested": [{"tags": {"Owner": "team"}}],
    }


def test_strip_ignored_tags_removes_multiple_configured_tags() -> None:
    value = {
        "tags": {"Name": "bucket", "Build": "123", "Version": "v1"},
        "tags_all": {"Environment": "dev", "Build": "123", "Version": "v1"},
    }

    assert strip_ignored_tags(value, {"Build", "Version"}) == {
        "tags": {"Name": "bucket"},
        "tags_all": {"Environment": "dev"},
    }


def test_changed_paths_omits_version_tag_and_limits_output() -> None:
    before = strip_version_tag(
        {
            "bucket": "old",
            "acl": "private",
            "tags": {"Name": "old", "Version": "old"},
        },
        "Version",
    )
    after = strip_version_tag(
        {
            "bucket": "new",
            "acl": "public-read",
            "tags": {"Name": "new", "Version": "new"},
        },
        "Version",
    )

    assert changed_paths(before, after, max_changed_fields=2) == "acl, bucket, ..."
