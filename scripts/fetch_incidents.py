"""
Fetches real, publicly-available GitHub issues and converts them into
incident-report-style markdown files under data/raw/incidents/.

This is the actual open-data source for the "incident reports" corpus: every
field in the generated markdown (title, issue number, body, labels, dates,
URL) comes directly from GitHub's public REST API for the configured repo.

Usage:
    python scripts/fetch_incidents.py
    python scripts/fetch_incidents.py --repo fastapi/fastapi --label bug --pages 3
    GITHUB_TOKEN=ghp_xxx python scripts/fetch_incidents.py --pages 5

Set GITHUB_TOKEN (a plain "read:public_repo" token is enough) to raise the
unauthenticated 60-requests/hour GitHub API limit to 5000/hour if you want a
much larger incident corpus.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

OUT_DIR = config.CORPORA["incidents"]


def slugify(text: str, max_len: int = 60) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text[:max_len].strip("-")


def clean_body(body: str) -> str:
    if not body:
        return "_No description provided._"
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def fetch_page(repo: str, label: str, page: int, token: str | None) -> list:
    url = (
        f"https://api.github.com/repos/{repo}/issues"
        f"?state=closed&labels={label}&per_page=40&page={page}&sort=updated&direction=desc"
    )
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "engineering-intelligence-hub")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP error on page {page}: {e.code} {e.reason}", file=sys.stderr)
        return []


def write_incident(issue: dict) -> bool:
    if "pull_request" in issue:
        return False
    number = issue["number"]
    title = issue["title"]
    labels = [l["name"] for l in issue.get("labels", [])]
    body = clean_body(issue.get("body") or "")
    created = issue.get("created_at", "")[:10]
    closed = issue.get("closed_at", "")[:10] if issue.get("closed_at") else "unresolved"
    url = issue.get("html_url", "")
    comments = issue.get("comments", 0)

    doc = f"""# Incident Report: {title}

**Source issue:** #{number} ({url})
**Status:** {issue.get('state', 'unknown')}
**Labels:** {', '.join(labels) if labels else 'none'}
**Reported:** {created}
**Resolved:** {closed}
**Discussion comments:** {comments}

## Reported Problem

{body}

## Resolution

This issue was closed on {closed}. See the linked GitHub issue and any
referenced pull requests at {url} for the exact code change that resolved it.
"""
    fname = f"{number}-{slugify(title)}.md"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / fname).write_text(doc, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="fastapi/fastapi")
    parser.add_argument("--label", default="bug")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--token", default=config.GITHUB_TOKEN)
    args = parser.parse_args()

    written = 0
    for page in range(1, args.pages + 1):
        print(f"Fetching {args.repo} closed '{args.label}' issues, page {page}...")
        issues = fetch_page(args.repo, args.label, page, args.token)
        if not issues:
            break
        for issue in issues:
            if write_incident(issue):
                written += 1
        time.sleep(1)  # be polite to the API

    print(f"Wrote {written} incident report files to {OUT_DIR}")


if __name__ == "__main__":
    main()
