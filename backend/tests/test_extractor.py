from types import SimpleNamespace

import pytest

from backend.extractor.claude_extractor import _parse_extraction, _response_text, _sniff_media_type
from backend.extractor.factory import get_extractor


def block(type_, text=None):
    return SimpleNamespace(type=type_, text=text)


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


def test_response_text_single_text_block():
    assert _response_text([block("text", '{"origin_country": "Colombia"}')]) == '{"origin_country": "Colombia"}'


def test_response_text_ignores_leading_non_text_block():
    # The actual bug seen in production: content[0] wasn't a usable text
    # block, and blindly trusting content[0].text produced an empty string.
    blocks = [block("thinking", ""), block("text", '{"origin_country": "Colombia"}')]
    assert _response_text(blocks) == '{"origin_country": "Colombia"}'


def test_response_text_strips_markdown_fence():
    blocks = [block("text", '```json\n{"origin_country": "Colombia"}\n```')]
    assert _response_text(blocks) == '{"origin_country": "Colombia"}'


def test_response_text_strips_bare_fence():
    blocks = [block("text", '```\n{"origin_country": "Colombia"}\n```')]
    assert _response_text(blocks) == '{"origin_country": "Colombia"}'


def test_parse_extraction_success():
    blocks = [block("text", '{"origin_country": "Colombia", "roast_level": "light"}')]
    assert _parse_extraction(blocks) == {"origin_country": "Colombia", "roast_level": "light"}


def test_parse_extraction_empty_response_raises_value_error_with_context():
    blocks = [block("text", "")]
    with pytest.raises(ValueError, match="did not return valid JSON"):
        _parse_extraction(blocks)
