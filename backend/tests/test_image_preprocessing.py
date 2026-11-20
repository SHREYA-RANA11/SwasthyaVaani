
from io import BytesIO

import pytest
from PIL import Image, ImageDraw, ImageFilter
from app.services.ai import (
    _preprocess_image,
    assess_image_quality,
    AIError,
)

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
def test_image_quality_assessment_returns_metrics():
    original = create_image("JPEG", size=(1200, 1600))

    result = assess_image_quality(original)

    assert result["width"] == 1200
    assert result["height"] == 1600
    assert "brightness" in result
    assert "contrast" in result
    assert "sharpness" in result
    assert isinstance(result["warnings"], list)


def test_image_quality_rejects_invalid_image():
    with pytest.raises(AIError):
        assess_image_quality(b"invalid image data")
def test_detects_dark_image():
    original = create_image("JPEG", size=(1200, 1600), mode="RGB")
    dark = Image.new("RGB", (1200, 1600), (20, 20, 20))

    buffer = BytesIO()
    dark.save(buffer, format="JPEG")

    result = assess_image_quality(buffer.getvalue())

    assert "image_too_dark" in result["warnings"]


def test_detects_bright_image():
    bright = Image.new("RGB", (1200, 1600), (255, 255, 255))

    buffer = BytesIO()
    bright.save(buffer, format="JPEG")

    result = assess_image_quality(buffer.getvalue())

    assert "image_too_bright" in result["warnings"]


def test_detects_low_contrast():
    low_contrast = Image.new("RGB", (1200, 1600), (125, 125, 125))

    buffer = BytesIO()
    low_contrast.save(buffer, format="JPEG")

    result = assess_image_quality(buffer.getvalue())

    assert "low_contrast" in result["warnings"]
def test_detects_blurry_image():
    sharp = Image.new("RGB", (1200, 1600), "white")
    draw = ImageDraw.Draw(sharp)

    draw.text((100, 200), "Prescription: Paracetamol 500 mg", fill="black")
    draw.text((100, 300), "Take twice daily after meals", fill="black")
    draw.text((100, 400), "Duration: 5 days", fill="black")

    blurry = sharp.filter(ImageFilter.GaussianBlur(radius=8))

    buffer = BytesIO()
    blurry.save(buffer, format="JPEG")

    result = assess_image_quality(buffer.getvalue())

    assert "possible_blur" in result["warnings"]
def test_sharp_text_is_not_flagged_as_blurry():
    sharp = Image.new("RGB", (1200, 1600), "white")
    draw = ImageDraw.Draw(sharp)

    draw.text(
        (100, 200),
        "Prescription: Paracetamol 500 mg",
        fill="black",
    )
    draw.text(
        (100, 300),
        "Take twice daily after meals",
        fill="black",
    )
    draw.text(
        (100, 400),
        "Duration: 5 days",
        fill="black",
    )

    buffer = BytesIO()
    sharp.save(buffer, format="JPEG")

    result = assess_image_quality(buffer.getvalue())

    assert "possible_blur" not in result["warnings"]