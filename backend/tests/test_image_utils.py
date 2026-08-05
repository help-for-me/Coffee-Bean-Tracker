from backend.image_utils import sniff_image_type


def test_sniff_image_type_jpeg():
    assert sniff_image_type(b"\xff\xd8\xff rest of file") == "image/jpeg"


def test_sniff_image_type_png():
    assert sniff_image_type(b"\x89PNG\r\n\x1a\n rest of file") == "image/png"


def test_sniff_image_type_gif():
    assert sniff_image_type(b"GIF89a rest of file") == "image/gif"


def test_sniff_image_type_webp():
    assert sniff_image_type(b"RIFF____WEBP rest of file") == "image/webp"


def test_sniff_image_type_unrecognized_returns_none():
    assert sniff_image_type(b"not an image, just some text") is None


def test_sniff_image_type_empty_bytes_returns_none():
    assert sniff_image_type(b"") is None
