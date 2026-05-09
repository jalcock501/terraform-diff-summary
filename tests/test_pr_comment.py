from __future__ import annotations

import json

from terraform_plan_summary.pr_comment import (
    build_comment_body,
    comment_marker,
    find_existing_comment,
    pull_request_number_from_event,
    upsert_pull_request_comment,
)


def test_build_comment_body_includes_stable_marker_and_summary() -> None:
    body = build_comment_body("Terraform diff summary", "### Terraform plan summary\n")

    assert comment_marker("Terraform diff summary") in body
    assert "## Terraform diff summary" in body
    assert "### Terraform plan summary" in body


def test_find_existing_comment_uses_marker() -> None:
    existing = {
        "url": "https://api.github.com/repos/example/repo/issues/comments/1",
        "body": build_comment_body("Terraform diff summary", "old summary"),
    }
    comments = [{"body": "unrelated"}, existing]

    assert find_existing_comment(comments, "Terraform diff summary") == existing


def test_pull_request_number_from_event_reads_pull_request_payload(tmp_path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"pull_request": {"number": 123}}),
        encoding="utf-8",
    )

    assert pull_request_number_from_event(str(event_path)) == 123


def test_pull_request_number_from_event_returns_none_for_non_pr_event(tmp_path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"ref": "refs/heads/main"}), encoding="utf-8")

    assert pull_request_number_from_event(str(event_path)) is None


def test_upsert_pull_request_comment_creates_when_missing(monkeypatch) -> None:
    calls = []

    def fake_github_request(method, url, token, payload=None):
        calls.append((method, url, token, payload))
        if method == "GET":
            return []
        return {"id": 1}

    monkeypatch.setattr(
        "terraform_plan_summary.pr_comment.github_request",
        fake_github_request,
    )

    result = upsert_pull_request_comment(
        repo="example/repo",
        pull_request_number=10,
        token="token",
        comment_title="Terraform diff summary",
        summary="summary",
        api_url="https://api.example.test",
    )

    assert result == "created"
    assert calls[0][0] == "GET"
    assert calls[1][0] == "POST"
    assert calls[1][3]["body"].endswith("summary")


def test_upsert_pull_request_comment_updates_existing(monkeypatch) -> None:
    existing_body = build_comment_body("Terraform diff summary", "old")
    calls = []

    def fake_github_request(method, url, token, payload=None):
        calls.append((method, url, token, payload))
        if method == "GET":
            return [
                {
                    "url": "https://api.example.test/comment/1",
                    "body": existing_body,
                }
            ]
        return {"id": 1}

    monkeypatch.setattr(
        "terraform_plan_summary.pr_comment.github_request",
        fake_github_request,
    )

    result = upsert_pull_request_comment(
        repo="example/repo",
        pull_request_number=10,
        token="token",
        comment_title="Terraform diff summary",
        summary="new",
        api_url="https://api.example.test",
    )

    assert result == "updated"
    assert calls[1][0] == "PATCH"
    assert calls[1][1] == "https://api.example.test/comment/1"
    assert calls[1][3]["body"].endswith("new")
