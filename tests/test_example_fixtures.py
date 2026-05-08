from __future__ import annotations

import json
from pathlib import Path

import pytest

from terraform_plan_summary.render import render_summary

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "example_tfplan"


@pytest.mark.parametrize(
    ("fixture_name", "expected_markers"),
    [
        (
            "tfplan-json-small-clean-sanitized.json",
            [
                "| Resource changes | 4 |",
                "| Changes shown below | 4 |",
                "#### Creates (1)",
                "#### Updates (3)",
            ],
        ),
        (
            "tfplan-json-noisy-sanitized.json",
            [
                "| Resource changes | 66 |",
                "| Changes shown below | 66 |",
                "#### Replacements (16)",
                "#### Creates (9)",
                "#### Updates (41)",
            ],
        ),
        (
            "tfplan-json-huge-noisy-sanitized.json",
            [
                "| Resource changes | 233 |",
                "| Changes shown below | 233 |",
                "#### Replacements (128)",
                "#### Creates (28)",
                "#### Updates (77)",
            ],
        ),
    ],
)
def test_example_tfplan_fixtures_render_expected_summary_markers(
    fixture_name: str,
    expected_markers: list[str],
) -> None:
    plan = json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))

    summary = render_summary(plan, ignored_tag_names=["Version"])

    for marker in expected_markers:
        assert marker in summary


def test_malformed_action_fixture_is_rendered_as_other_change() -> None:
    plan = json.loads(
        (FIXTURE_DIR / "tfplan-json-broken-negative-test-sanitized.json").read_text(
            encoding="utf-8"
        )
    )

    summary = render_summary(plan, ignored_tag_names=["Version"])

    assert "| Resource changes | 4 |" in summary
    assert "#### Replacements (1)" in summary
    assert "#### Other changes (1)" in summary
    assert "| `null_resource.example` | `replace` | `null_resource` | `triggers.a` |" in summary
