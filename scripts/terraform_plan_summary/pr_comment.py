"""GitHub pull request comment support."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

DEFAULT_COMMENT_TITLE = "Terraform diff summary"


def comment_marker(comment_title: str) -> str:
    digest = hashlib.sha256(comment_title.encode("utf-8")).hexdigest()[:12]
    return f"<!-- terraform-diff-summary:{digest} -->"


def build_comment_body(comment_title: str, summary: str) -> str:
    marker = comment_marker(comment_title)
    return f"{marker}\n## {comment_title}\n\n{summary}"


def find_existing_comment(
    comments: list[dict[str, Any]], comment_title: str
) -> dict[str, Any] | None:
    marker = comment_marker(comment_title)
    for comment in comments:
        if marker in str(comment.get("body", "")):
            return comment
    return None


def pull_request_number_from_event(event_path: str | None) -> int | None:
    if not event_path:
        return None

    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Could not read GitHub event payload {event_path!r}.") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Could not parse GitHub event payload {event_path!r} as JSON."
        ) from exc

    pull_request = event.get("pull_request")
    if isinstance(pull_request, dict) and pull_request.get("number") is not None:
        return int(pull_request["number"])

    return None


def github_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"GitHub API request failed: {method} {url} returned "
            f"{exc.code}: {error_body}"
        ) from exc

    if not response_body:
        return None
    return json.loads(response_body)


def list_pull_request_comments(
    *,
    repo: str,
    pull_request_number: int,
    token: str,
    comment_title: str,
    api_url: str = "https://api.github.com",
) -> list[dict[str, Any]]:
    collected_comments = []
    page = 1

    while True:
        query = urlencode(
            {
                "per_page": "100",
                "page": str(page),
                "sort": "updated",
                "direction": "desc",
            }
        )
        comments_url = (
            f"{api_url}/repos/{repo}/issues/{pull_request_number}/comments?{query}"
        )
        comments = github_request("GET", comments_url, token)
        if not comments:
            return collected_comments

        collected_comments.extend(comments)
        if find_existing_comment(comments, comment_title):
            return collected_comments

        if len(comments) < 100:
            return collected_comments

        page += 1


def upsert_pull_request_comment(
    *,
    repo: str,
    pull_request_number: int,
    token: str,
    comment_title: str,
    summary: str,
    api_url: str = "https://api.github.com",
) -> str:
    comments = list_pull_request_comments(
        repo=repo,
        pull_request_number=pull_request_number,
        token=token,
        comment_title=comment_title,
        api_url=api_url,
    )
    body = build_comment_body(comment_title, summary)
    existing_comment = find_existing_comment(comments, comment_title)

    if existing_comment:
        comment_url = str(existing_comment["url"])
        github_request("PATCH", comment_url, token, {"body": body})
        return "updated"

    create_url = f"{api_url}/repos/{repo}/issues/{pull_request_number}/comments"
    github_request("POST", create_url, token, {"body": body})
    return "created"


def post_pull_request_comment_from_env(summary: str, comment_title: str) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    pull_request_number = pull_request_number_from_event(
        os.environ.get("GITHUB_EVENT_PATH")
    )

    if not token:
        raise SystemExit("COMMENT_ON_PR requires GITHUB_TOKEN to be available.")

    if not repo:
        raise SystemExit("COMMENT_ON_PR requires GITHUB_REPOSITORY to be available.")

    if pull_request_number is None:
        print("COMMENT_ON_PR is true, but this event is not a pull_request; skipping.")
        return

    result = upsert_pull_request_comment(
        repo=repo,
        pull_request_number=pull_request_number,
        token=token,
        comment_title=comment_title,
        summary=summary,
    )
    print(f"Pull request comment {result}.")
