from __future__ import annotations

import json

import pytest

from terraform_plan_summary.pr_comment import (
    build_comment_body,
    comment_marker,
    find_existing_comment,
    list_pull_request_comments,
    post_pull_request_comment_from_env,
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


def test_pull_request_number_from_event_fails_clearly_for_missing_file() -> None:
    with pytest.raises(SystemExit, match="Could not read GitHub event payload"):
        pull_request_number_from_event("missing-event.json")


def test_pull_request_number_from_event_fails_clearly_for_invalid_json(
    tmp_path,
) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text("{", encoding="utf-8")

    with pytest.raises(SystemExit, match="Could not parse GitHub event payload"):
        pull_request_number_from_event(str(event_path))


def test_list_pull_request_comments_paginates_until_marker_is_found(
    monkeypatch,
) -> None:
    marked_comment = {
        "url": "https://api.example.test/comment/101",
        "body": build_comment_body("Terraform diff summary", "old"),
    }
    pages = [
        [{"body": f"unrelated {index}"} for index in range(100)],
        [marked_comment],
    ]
    urls = []

    def fake_github_request(method, url, token, payload=None):
        urls.append(url)
        return pages.pop(0)

    monkeypatch.setattr(
        "terraform_plan_summary.pr_comment.github_request",
        fake_github_request,
    )

    comments = list_pull_request_comments(
        repo="example/repo",
        pull_request_number=10,
        token="token",
        comment_title="Terraform diff summary",
        api_url="https://api.example.test",
    )

    assert marked_comment in comments
    assert "page=1" in urls[0]
    assert "page=2" in urls[1]
    assert "sort=updated" in urls[0]
    assert "direction=desc" in urls[0]


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


def test_post_pull_request_comment_from_env_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/repo")
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)

    with pytest.raises(SystemExit, match="GITHUB_TOKEN"):
        post_pull_request_comment_from_env("summary", "Terraform diff summary")


def test_post_pull_request_comment_from_env_requires_repository(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)

    with pytest.raises(SystemExit, match="GITHUB_REPOSITORY"):
        post_pull_request_comment_from_env("summary", "Terraform diff summary")


def test_post_pull_request_comment_from_env_skips_non_pr_event(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"ref": "refs/heads/main"}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/repo")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

    post_pull_request_comment_from_env("summary", "Terraform diff summary")

    assert "not a pull_request" in capsys.readouterr().out


def test_post_pull_request_comment_from_env_posts_for_pr_event(
    monkeypatch,
    tmp_path,
) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"pull_request": {"number": 10}}),
        encoding="utf-8",
    )
    calls = []

    def fake_upsert_pull_request_comment(**kwargs):
        calls.append(kwargs)
        return "created"

    monkeypatch.setattr(
        "terraform_plan_summary.pr_comment.upsert_pull_request_comment",
        fake_upsert_pull_request_comment,
    )
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/repo")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

    post_pull_request_comment_from_env("summary", "Terraform diff summary")

    assert calls == [
        {
            "repo": "example/repo",
            "pull_request_number": 10,
            "token": "token",
            "comment_title": "Terraform diff summary",
            "summary": "summary",
        }
    ]
