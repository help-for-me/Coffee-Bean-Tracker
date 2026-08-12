import json

import httpx
import pytest

from backend.exports.github_sink import GithubSinkNotConfigured, push_to_github


def test_push_to_github_requires_token_and_repo(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    with pytest.raises(GithubSinkNotConfigured):
        push_to_github(b"data", "backup.xlsx")


def test_push_to_github_requires_repo_even_with_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    with pytest.raises(GithubSinkNotConfigured):
        push_to_github(b"data", "backup.xlsx")


def test_push_to_github_creates_file_when_none_exists(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "someuser/somerepo")
    requests_made = []

    def handler(request):
        requests_made.append(request.method)
        if request.method == "GET":
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(201, json={"content": {"sha": "abc123"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = push_to_github(b"file bytes", "backup.xlsx", client=client)

    assert result["content"]["sha"] == "abc123"
    assert requests_made == ["GET", "PUT"]


def test_push_to_github_updates_existing_file_with_its_sha(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "someuser/somerepo")
    put_payloads = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"sha": "existing-sha"})
        put_payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"content": {"sha": "new-sha"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    push_to_github(b"file bytes", "backup.xlsx", client=client)

    assert put_payloads[0]["sha"] == "existing-sha"


def test_push_to_github_encodes_content_as_base64(monkeypatch):
    import base64

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "someuser/somerepo")
    put_payloads = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(404, json={})
        put_payloads.append(json.loads(request.content))
        return httpx.Response(201, json={"content": {"sha": "abc"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    push_to_github(b"hello world", "backup.xlsx", client=client)

    assert base64.b64decode(put_payloads[0]["content"]) == b"hello world"


def test_push_to_github_raises_on_http_error(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "someuser/somerepo")

    def handler(request):
        if request.method == "GET":
            return httpx.Response(404, json={})
        return httpx.Response(422, json={"message": "Validation failed"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        push_to_github(b"file bytes", "backup.xlsx", client=client)


def test_push_to_github_uses_default_branch_main(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "someuser/somerepo")
    monkeypatch.delenv("GITHUB_BRANCH", raising=False)
    put_payloads = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(404, json={})
        put_payloads.append(json.loads(request.content))
        return httpx.Response(201, json={"content": {"sha": "abc"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    push_to_github(b"data", "backup.xlsx", client=client)

    assert put_payloads[0]["branch"] == "main"
