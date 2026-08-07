from __future__ import annotations

import hashlib
from io import BytesIO

from PIL import Image, PngImagePlugin


def photo_bytes(image_format: str, seed: bytes = b"nodo-photo-fixture") -> bytes:
    digest = hashlib.sha256(seed).digest()
    image = Image.new("RGB", (2, 2), color=tuple(digest[:3]))
    output = BytesIO()
    if image_format.upper() == "PNG":
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("fixture", digest.hex())
        image.save(output, format="PNG", pnginfo=metadata)
    else:
        image.save(output, format=image_format.upper())
    return output.getvalue()


def png_bytes(seed: bytes = b"nodo-png-fixture") -> bytes:
    return photo_bytes("PNG", seed)
