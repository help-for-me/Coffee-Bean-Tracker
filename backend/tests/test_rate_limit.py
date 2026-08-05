from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.rate_limit import enforce_cooldown


def _request(ip="1.2.3.4"):
    return SimpleNamespace(client=SimpleNamespace(host=ip))


def test_enforce_cooldown_allows_first_call():
    enforce_cooldown(_request(), "test:allow-first", seconds=30)


def test_enforce_cooldown_blocks_immediate_repeat():
    key = "test:blocks-repeat"
    enforce_cooldown(_request(), key, seconds=30)
    with pytest.raises(HTTPException) as exc_info:
        enforce_cooldown(_request(), key, seconds=30)
    assert exc_info.value.status_code == 429


def test_enforce_cooldown_is_scoped_per_client_ip():
    key = "test:per-ip"
    enforce_cooldown(_request("1.1.1.1"), key, seconds=30)
    # A different client hitting the same key isn't blocked by the first
    # client's cooldown.
    enforce_cooldown(_request("2.2.2.2"), key, seconds=30)


def test_enforce_cooldown_is_scoped_per_key():
    ip = "1.2.3.4"
    enforce_cooldown(_request(ip), "test:key-a", seconds=30)
    # A different action key for the same client isn't blocked either.
    enforce_cooldown(_request(ip), "test:key-b", seconds=30)


def test_enforce_cooldown_zero_seconds_never_blocks():
    key = "test:zero-cooldown"
    enforce_cooldown(_request(), key, seconds=0)
    enforce_cooldown(_request(), key, seconds=0)


def test_enforce_cooldown_handles_missing_client():
    # request.client can be None (some test/proxy setups) - must not crash.
    enforce_cooldown(SimpleNamespace(client=None), "test:no-client", seconds=30)
