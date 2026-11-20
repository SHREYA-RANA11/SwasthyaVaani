
from io import BytesIO

import pytest
from PIL import Image

from app.services.ai import _preprocess_image, AIError


def create_image(format="JPEG", size=(100, 100), mode="RGB"):
    buffer = BytesIO()

    if mode == "RGBA":
        image = Image.new("RGBA", size, (255, 0, 0, 100))
    else:
        image = Image.new(mode, size, "white")

    image.save(buffer, format=format)
    return buffer.getvalue()


def test_jpeg_preprocessing():
    original = create_image("JPEG")

    processed, mime = _preprocess_image(original, "image/jpeg")

    assert mime == "image/jpeg"

    with Image.open(BytesIO(processed)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"


def test_png_preprocessing():
    original = create_image("PNG")

    processed, mime = _preprocess_image(original, "image/png")

    assert mime == "image/jpeg"

    with Image.open(BytesIO(processed)) as image:
        assert image.format == "JPEG"


def test_transparent_png_preprocessing():
    original = create_image("PNG", mode="RGBA")

    processed, mime = _preprocess_image(original, "image/png")

    with Image.open(BytesIO(processed)) as image:
        assert image.mode == "RGB"
        assert image.format == "JPEG"
        pixel = image.getpixel((50, 50))
        assert pixel[0] > 240
        assert 130 < pixel[1] < 180
        assert 130 < pixel[2] < 180


def test_large_image_resizing():
    original = create_image("PNG", size=(3000, 2000))

    processed, mime = _preprocess_image(original, "image/png")

    with Image.open(BytesIO(processed)) as image:
        assert image.size == (2400, 1600)


def test_invalid_image_rejected():
    invalid_data = b"this is not a valid image"

    with pytest.raises(AIError):
        _preprocess_image(invalid_data, "image/jpeg")


def test_small_image_dimensions_preserved():
    original = create_image("JPEG", size=(400, 300))

    processed, mime = _preprocess_image(original, "image/jpeg")

    with Image.open(BytesIO(processed)) as image:
        assert image.size == (400, 300)
