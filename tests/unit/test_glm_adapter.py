"""Unit tests for GLM-OCR multimodal adapter."""

import pytest
from PIL import Image
import io

from docintel.ocr.glm_adapter import GLMOCRAdapter
from docintel.core.schemas import BoundingBox, CoordSystem


@pytest.mark.asyncio
async def test_glm_adapter_initialization():
    adapter = GLMOCRAdapter()
    assert adapter.name == "glm_ocr"
    assert adapter.model_id == "zai-org/GLM-OCR"
    assert isinstance(adapter.is_available, bool)


@pytest.mark.asyncio
async def test_glm_adapter_coordinate_parsing():
    adapter = GLMOCRAdapter()
    # Test normalized 0-1000 coordinate parsing
    raw_glm_output = "[50, 100, 450, 200] Invoice Title\n[50, 220, 500, 350] Total Amount: $1,250.00"
    tokens, md = adapter._parse_glm_output(raw_glm_output, img_width=1000, img_height=1000)

    assert len(tokens) == 2
    assert tokens[0].text == "Invoice Title"
    assert tokens[0].bbox.x0 == 50.0
    assert tokens[0].bbox.y0 == 100.0
    assert tokens[0].bbox.x1 == 450.0
    assert tokens[0].bbox.y1 == 200.0
    assert tokens[0].bbox.coord_system == CoordSystem.PIXEL


@pytest.mark.asyncio
async def test_glm_adapter_process_image():
    adapter = GLMOCRAdapter()
    img = Image.new("RGB", (600, 800), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    res = await adapter.process_image(buf.getvalue())
    assert res is not None
    assert res.model_name == "glm_ocr_0.9b"
    assert res.latency_ms > 0
    assert len(res.tokens) > 0
    assert res.tokens[0].bbox.x1 > res.tokens[0].bbox.x0
