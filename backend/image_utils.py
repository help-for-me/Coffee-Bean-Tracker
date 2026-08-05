from typing import Optional

# Shared by extractor/claude_extractor.py (picking the right media_type to
# send the Anthropic API) and photos.py (rejecting uploads that aren't
# actually images) - checks the file's real bytes rather than trusting
# whatever content-type/extension the client sent.


def sniff_image_type(data: bytes) -> Optional[str]:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
