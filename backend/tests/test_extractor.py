from types import SimpleNamespace

import pytest

from backend.extractor.claude_extractor import (
    _correct_against_vocab,
    _parse_extraction,
    _response_text,
    _sniff_media_type,
    _strip_coferment_wording,
    normalize_extraction,
)
from backend.extractor.coffee_vocab import KNOWN_PROCESSES, KNOWN_VARIETIES
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


# --- normalization: real bug seen on the Elkin Guzman / Pallet Coffee bag ---
# The model dumped "Mango Co-Fermented" into process alongside the real
# process, instead of keeping it exclusively in co_ferment_ingredient.


def test_strip_coferment_wording_removes_coferment_segment():
    assert _strip_coferment_wording("Washed, Mango Co-Fermented") == "Washed"


def test_strip_coferment_wording_handles_variant_spelling():
    assert _strip_coferment_wording("Honey, Lychee Coferment") == "Honey"


def test_strip_coferment_wording_returns_none_if_nothing_left():
    assert _strip_coferment_wording("Co-Fermented") is None


def test_strip_coferment_wording_leaves_plain_process_alone():
    assert _strip_coferment_wording("Washed") == "Washed"


def test_strip_coferment_wording_handles_none():
    assert _strip_coferment_wording(None) is None


def test_correct_against_vocab_fixes_close_typo():
    assert _correct_against_vocab("Castllo", KNOWN_VARIETIES) == "Castillo"


def test_correct_against_vocab_leaves_unknown_term_untouched():
    # A real but uncommon term shouldn't get remapped to the nearest known
    # one - only close-enough typos of known terms get corrected.
    assert _correct_against_vocab("Sidra", KNOWN_VARIETIES) == "Sidra"


def test_correct_against_vocab_handles_multiple_segments():
    assert _correct_against_vocab("Castillo, Caturaa", KNOWN_VARIETIES) == "Castillo, Caturra"


def test_normalize_extraction_strips_coferment_from_process():
    result = normalize_extraction({"process": "Washed, Mango Co-Fermented", "variety": "Caturra"})
    assert result["process"] == "Washed"


def test_normalize_extraction_corrects_process_typo():
    result = normalize_extraction({"process": "Anerobic"})
    assert result["process"] == "Anaerobic"
    assert "Anaerobic" in KNOWN_PROCESSES


def test_normalize_extraction_leaves_other_fields_untouched():
    result = normalize_extraction({"origin_country": "Colombia", "region": None})
    assert result == {"origin_country": "Colombia", "region": None}


def test_normalize_extraction_handles_missing_process_and_variety():
    assert normalize_extraction({"origin_country": "Colombia"}) == {"origin_country": "Colombia"}
