import base64
import os
from typing import Optional

import httpx


class GithubSinkNotConfigured(Exception):
    pass


def push_to_github(content: bytes, path: str, client: Optional[httpx.Client] = None) -> dict:
    # Pushes `content` to `path` in a separate, dedicated private backup
    # repo via GitHub's Contents API - a plain httpx REST call rather than
    # a PyGithub dependency, since this is the only GitHub API call the
    # app makes. Creating vs. updating the file is the same API call, but
    # updating requires the existing file's sha, so that's fetched first.
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO")
    branch = os.environ.get("GITHUB_BRANCH", "main")
    if not (token and repo):
        raise GithubSinkNotConfigured("GITHUB_TOKEN and GITHUB_REPO must both be set - see .env.example.")

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    owns_client = client is None
    client = client or httpx.Client(timeout=30)
    try:
        existing = client.get(url, headers=headers, params={"ref": branch})
        sha = existing.json().get("sha") if existing.status_code == 200 else None

        payload = {
            "message": f"Coffee Bean Tracker backup - {path}",
            "content": base64.b64encode(content).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        response = client.put(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    finally:
        if owns_client:
            client.close()
