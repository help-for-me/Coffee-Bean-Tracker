import pytest

from backend.extractor.claude_extractor import _sniff_media_type
from backend.extractor.factory import get_extractor


def test_sniff_media_type_png():
    assert _sniff_media_type(b"\x89PNG\r\n\x1a\n rest of file") == "image/png"


def test_sniff_media_type_jpeg():
    assert _sniff_media_type(b"\xff\xd8\xff rest of file") == "image/jpeg"


def test_sniff_media_type_unknown_defaults_to_jpeg():
    assert _sniff_media_type(b"not-an-image") == "image/jpeg"


def test_factory_ollama_not_implemented(monkeypatch):
    monkeypatch.setenv("EXTRACTOR_PROVIDER", "ollama")
    with pytest.raises(NotImplementedError):
        get_extractor()


def test_factory_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("EXTRACTOR_PROVIDER", "bogus")
    with pytest.raises(ValueError):
        get_extractor()


def test_factory_claude_requires_api_key(monkeypatch):
    monkeypatch.setenv("EXTRACTOR_PROVIDER", "claude")
    with pytest.raises(KeyError):
        get_extractor()
