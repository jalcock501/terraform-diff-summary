import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from terraform_diff_summary import (  # noqa: E402
    changed_paths,
    is_version_tag_only,
    main,
    render_summary,
    strip_version_tag,
)


def resource_change(address, resource_type, actions, before, after):
    return {
        "address": address,
        "type": resource_type,
        "change": {
            "actions": actions,
            "before": before,
            "after": after,
        },
    }


def test_strip_version_tag_removes_configured_tag_from_tags_and_tags_all():
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


def test_version_tag_only_update_is_filtered():
    change = resource_change(
        "aws_s3_bucket.example",
        "aws_s3_bucket",
        ["update"],
        {"tags": {"Name": "example", "Version": "old"}},
        {"tags": {"Name": "example", "Version": "new"}},
    )

    assert is_version_tag_only(change, "Version")


def test_update_with_other_changes_is_not_version_tag_only():
    change = resource_change(
        "aws_s3_bucket.example",
        "aws_s3_bucket",
        ["update"],
        {"bucket": "old", "tags": {"Name": "example", "Version": "old"}},
        {"bucket": "new", "tags": {"Name": "example", "Version": "new"}},
    )

    assert not is_version_tag_only(change, "Version")


def test_changed_paths_omits_version_tag_and_limits_output():
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


def test_render_summary_filters_version_only_changes_and_shows_changed_fields():
    plan = {
        "resource_changes": [
            resource_change(
                "aws_s3_bucket.version_only",
                "aws_s3_bucket",
                ["update"],
                {"tags": {"Name": "same", "Version": "old"}},
                {"tags": {"Name": "same", "Version": "new"}},
            ),
            resource_change(
                "aws_s3_bucket.real_change",
                "aws_s3_bucket",
                ["update"],
                {"bucket": "old", "tags": {"Name": "old", "Version": "old"}},
                {"bucket": "new", "tags": {"Name": "new", "Version": "new"}},
            ),
            resource_change(
                "aws_s3_bucket.noop",
                "aws_s3_bucket",
                ["no-op"],
                {"bucket": "same"},
                {"bucket": "same"},
            ),
        ]
    }

    summary = render_summary(plan, "Version", 8)

    assert "| Resource changes | 2 |" in summary
    assert "| Filtered Version tag-only changes | 1 |" in summary
    assert "| Changes shown below | 1 |" in summary
    assert "`aws_s3_bucket.real_change`" in summary
    assert "`bucket, tags.Name`" in summary
    assert "aws_s3_bucket.version_only`" not in summary
    assert "aws_s3_bucket.noop`" not in summary


def test_script_appends_summary_to_github_step_summary(tmp_path, monkeypatch):
    plan_path = tmp_path / "tfplan.json"
    summary_path = tmp_path / "summary.md"
    plan_path.write_text(
        json.dumps(
            {
                "resource_changes": [
                    resource_change(
                        "aws_s3_bucket.example",
                        "aws_s3_bucket",
                        ["create"],
                        None,
                        {"bucket": "new"},
                    )
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("PLAN_JSON_PATH", str(plan_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setenv("VERSION_TAG_NAME", "Version")
    monkeypatch.setenv("MAX_CHANGED_FIELDS", "8")

    main()

    assert "`aws_s3_bucket.example`" in summary_path.read_text(encoding="utf-8")
