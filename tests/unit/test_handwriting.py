"""Unit tests for Handwriting OCR and HTR stroke preprocessing."""

import pytest
from PIL import Image, ImageDraw
import io

from docintel.ocr.handwriting_adapter import HandwritingOCRAdapter
from docintel.ocr.preprocessing import (
    enhance_handwritten_strokes,
    detect_handwriting_presence,
)


@pytest.mark.asyncio
async def test_handwriting_adapter_initialization():
    adapter = HandwritingOCRAdapter()
    assert adapter.name == "handwriting"
    assert isinstance(adapter.is_available, bool)


@pytest.mark.asyncio
async def test_handwriting_stroke_enhancement():
    # Create white canvas with gray stroke
    img = Image.new("L", (200, 100), color=255)
    draw = ImageDraw.Draw(img)
    draw.line([(20, 50), (180, 50)], fill=120, width=3)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    enhanced = enhance_handwritten_strokes(raw_bytes)
    assert enhanced is not None
    assert len(enhanced) > 0


@pytest.mark.asyncio
async def test_detect_handwriting_presence():
    img = Image.new("L", (300, 300), color=255)
    draw = ImageDraw.Draw(img)
    # Draw curved freehand strokes
    draw.arc([(50, 50), (250, 250)], start=0, end=180, fill=0, width=4)

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    is_handwritten, score = detect_handwriting_presence(buf.getvalue())
    assert isinstance(is_handwritten, bool)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_handwriting_adapter_process_image():
    adapter = HandwritingOCRAdapter()
    img = Image.new("RGB", (500, 700), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((40, 60), "Handwritten Doctor Note", fill=(20, 20, 20))

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    res = await adapter.process_image(buf.getvalue())
    assert res is not None
    assert res.latency_ms > 0
    assert len(res.tokens) > 0
    assert res.extra.get("htr_optimized") is True
