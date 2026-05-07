from __future__ import annotations

from terraform_plan_summary.render import render_summary


def test_render_summary_filters_version_only_changes_and_shows_changed_fields(
    resource_change,
) -> None:
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
    assert "| Filtered tag-only changes (Version) | 1 |" in summary
    assert "| Changes shown below | 1 |" in summary
    assert "`aws_s3_bucket.real_change`" in summary
    assert "`bucket, tags.Name`" in summary
    assert "aws_s3_bucket.version_only`" not in summary
    assert "aws_s3_bucket.noop`" not in summary


def test_render_summary_can_disable_tag_only_filtering(resource_change) -> None:
    plan = {
        "resource_changes": [
            resource_change(
                "aws_s3_bucket.version_only",
                "aws_s3_bucket",
                ["update"],
                {"tags": {"Name": "same", "Version": "old"}},
                {"tags": {"Name": "same", "Version": "new"}},
            ),
        ]
    }

    summary = render_summary(
        plan,
        "Version",
        8,
        filter_tag_only_changes=False,
        summary_title="Custom Terraform summary",
    )

    assert "### Custom Terraform summary" in summary
    assert "| Filtered tag-only changes (Version) | 0 |" in summary
    assert "| Changes shown below | 1 |" in summary
    assert "`aws_s3_bucket.version_only`" in summary
    assert "`tags.Version`" in summary


def test_render_summary_respects_explicit_empty_ignored_tag_names(
    resource_change,
) -> None:
    plan = {
        "resource_changes": [
            resource_change(
                "aws_s3_bucket.version_only",
                "aws_s3_bucket",
                ["update"],
                {"tags": {"Name": "same", "Version": "old"}},
                {"tags": {"Name": "same", "Version": "new"}},
            ),
        ]
    }

    summary = render_summary(plan, "Version", 8, ignored_tag_names=[])

    assert "| Filtered tag-only changes () | 0 |" in summary
    assert "| Changes shown below | 1 |" in summary
    assert "`tags.Version`" in summary


def test_render_summary_escapes_ignored_tag_names_in_count_table(
    resource_change,
) -> None:
    plan = {
        "resource_changes": [
            resource_change(
                "aws_s3_bucket.example",
                "aws_s3_bucket",
                ["update"],
                {"bucket": "old", "tags": {"Team|Name": "old"}},
                {"bucket": "new", "tags": {"Team|Name": "new"}},
            ),
        ]
    }

    summary = render_summary(plan, ignored_tag_names=["Team|Name"])

    assert "| Filtered tag-only changes (Team\\|Name) | 0 |" in summary


def test_render_summary_groups_visible_changes_by_action(resource_change) -> None:
    plan = {
        "resource_changes": [
            resource_change(
                "aws_s3_bucket.created",
                "aws_s3_bucket",
                ["create"],
                None,
                {"bucket": "new"},
            ),
            resource_change(
                "aws_s3_bucket.replaced",
                "aws_s3_bucket",
                ["delete", "create"],
                {"bucket": "old"},
                {"bucket": "new"},
            ),
            resource_change(
                "aws_s3_bucket.deleted",
                "aws_s3_bucket",
                ["delete"],
                {"bucket": "old"},
                None,
            ),
        ]
    }

    summary = render_summary(plan, "Version", 8)

    replace_index = summary.index("#### Replacements (1)")
    delete_index = summary.index("#### Deletes (1)")
    create_index = summary.index("#### Creates (1)")

    assert replace_index < delete_index < create_index
    assert "`aws_s3_bucket.replaced`" in summary
    assert "`aws_s3_bucket.deleted`" in summary
    assert "`aws_s3_bucket.created`" in summary
