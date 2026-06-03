"""Shared image-processing utilities used across the application."""

import base64


def strip_base64_header(data_url: str) -> str:
    """Remove the `data:<mime>;base64,` prefix if present.

    Args:
        data_url: A raw base64 string or a full data-URL from the browser canvas.

    Returns:
        The base64-encoded payload without the header.
    """
    if "," in data_url:
        return data_url.split(",", 1)[1]
    return data_url


def decode_base64_image(data_url: str) -> bytes:
    """Decode a base64-encoded image (with or without a data-URL header) to bytes.

    Args:
        data_url: A raw base64 string or a full data-URL.

    Returns:
        The decoded image bytes.
    """
    clean_b64 = strip_base64_header(data_url)
    return base64.b64decode(clean_b64)


def encode_image_to_data_url(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """Encode raw image bytes into a complete data-URL string.

    Args:
        image_bytes: Raw image data.
        mime_type: The MIME type to embed in the data-URL header.

    Returns:
        A full data-URL string ready for use in an <img> src attribute.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"
