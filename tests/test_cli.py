from __future__ import annotations

import json

import pytest

from terraform_plan_summary.cli import main


def test_script_appends_summary_to_github_step_summary(
    tmp_path,
    monkeypatch,
    resource_change,
) -> None:
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
    monkeypatch.setenv("IGNORED_TAG_NAMES", "Version")
    monkeypatch.delenv("VERSION_TAG_NAME", raising=False)
    monkeypatch.setenv("FILTER_TAG_ONLY_CHANGES", "true")
    monkeypatch.setenv("MAX_CHANGED_FIELDS", "8")
    monkeypatch.setenv("SUMMARY_TITLE", "Terraform plan summary")

    main()

    assert "`aws_s3_bucket.example`" in summary_path.read_text(encoding="utf-8")


def test_script_can_append_summary_to_optional_output_path(
    tmp_path,
    monkeypatch,
    resource_change,
) -> None:
    plan_path = tmp_path / "tfplan.json"
    step_summary_path = tmp_path / "step-summary.md"
    output_summary_path = tmp_path / "output-summary.md"
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
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(step_summary_path))
    monkeypatch.setenv("SUMMARY_OUTPUT_PATH", str(output_summary_path))
    monkeypatch.setenv("IGNORED_TAG_NAMES", "Version")
    monkeypatch.setenv("FILTER_TAG_ONLY_CHANGES", "true")
    monkeypatch.setenv("MAX_CHANGED_FIELDS", "8")

    main()

    assert "`aws_s3_bucket.example`" in step_summary_path.read_text(
        encoding="utf-8"
    )
    assert "`aws_s3_bucket.example`" in output_summary_path.read_text(
        encoding="utf-8"
    )


def test_script_fails_after_summary_when_visible_destroy_is_present(
    tmp_path,
    monkeypatch,
    resource_change,
) -> None:
    plan_path = tmp_path / "tfplan.json"
    summary_path = tmp_path / "summary.md"
    plan_path.write_text(
        json.dumps(
            {
                "resource_changes": [
                    resource_change(
                        "aws_s3_bucket.deleted",
                        "aws_s3_bucket",
                        ["delete"],
                        {"bucket": "old"},
                        None,
                    )
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("PLAN_JSON_PATH", str(plan_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setenv("IGNORED_TAG_NAMES", "Version")
    monkeypatch.setenv("FILTER_TAG_ONLY_CHANGES", "true")
    monkeypatch.setenv("MAX_CHANGED_FIELDS", "8")
    monkeypatch.setenv("FAIL_ON_DESTROY", "true")
    monkeypatch.setenv("FAIL_ON_REPLACE", "false")

    with pytest.raises(SystemExit, match="1 destroy change"):
        main()

    assert "`aws_s3_bucket.deleted`" in summary_path.read_text(encoding="utf-8")


def test_script_fails_after_summary_when_visible_replace_is_present(
    tmp_path,
    monkeypatch,
    resource_change,
) -> None:
    plan_path = tmp_path / "tfplan.json"
    summary_path = tmp_path / "summary.md"
    plan_path.write_text(
        json.dumps(
            {
                "resource_changes": [
                    resource_change(
                        "aws_s3_bucket.replaced",
                        "aws_s3_bucket",
                        ["delete", "create"],
                        {"bucket": "old"},
                        {"bucket": "new"},
                    )
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("PLAN_JSON_PATH", str(plan_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setenv("IGNORED_TAG_NAMES", "Version")
    monkeypatch.setenv("FILTER_TAG_ONLY_CHANGES", "true")
    monkeypatch.setenv("MAX_CHANGED_FIELDS", "8")
    monkeypatch.setenv("FAIL_ON_DESTROY", "false")
    monkeypatch.setenv("FAIL_ON_REPLACE", "true")

    with pytest.raises(SystemExit, match="1 replacement change"):
        main()

    assert "`aws_s3_bucket.replaced`" in summary_path.read_text(encoding="utf-8")


def test_script_fails_clearly_for_invalid_max_changed_fields(
    tmp_path,
    monkeypatch,
) -> None:
    plan_path = tmp_path / "tfplan.json"
    summary_path = tmp_path / "summary.md"
    plan_path.write_text(json.dumps({"resource_changes": []}), encoding="utf-8")

    monkeypatch.setenv("PLAN_JSON_PATH", str(plan_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setenv("MAX_CHANGED_FIELDS", "many")

    with pytest.raises(SystemExit, match="Invalid integer value.*MAX_CHANGED_FIELDS"):
        main()


def test_script_fails_clearly_for_non_positive_max_changed_fields(
    tmp_path,
    monkeypatch,
) -> None:
    plan_path = tmp_path / "tfplan.json"
    summary_path = tmp_path / "summary.md"
    plan_path.write_text(json.dumps({"resource_changes": []}), encoding="utf-8")

    monkeypatch.setenv("PLAN_JSON_PATH", str(plan_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setenv("MAX_CHANGED_FIELDS", "0")

    with pytest.raises(SystemExit, match="MAX_CHANGED_FIELDS must be"):
        main()
