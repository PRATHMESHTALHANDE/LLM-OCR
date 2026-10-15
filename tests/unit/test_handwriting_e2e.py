import io
import pytest
from PIL import Image, ImageDraw

from docintel.extractors.docling_adapter import DoclingAdapter
from docintel.ocr.handwriting_adapter import HandwritingOCRAdapter


@pytest.mark.asyncio
async def test_handwriting_adapter_real_extraction():
    """Verify HandwritingOCRAdapter extracts actual words and valid pixel bounding boxes."""
    img = Image.new("RGB", (650, 350), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((40, 50), "Patient Name: Robert Smith", fill=(10, 10, 10))
    draw.text((40, 120), "Rx: Metformin 500mg daily", fill=(10, 10, 10))
    draw.text((40, 190), "Doctor Signature: Dr. House MD", fill=(10, 10, 10))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    adapter = HandwritingOCRAdapter()
    result = await adapter.process_image(raw_bytes)

    assert result is not None
    assert len(result.tokens) >= 3
    assert "Robert Smith" in result.text or "Metformin" in result.text
    for tok in result.tokens:
        assert tok.bbox.x1 > tok.bbox.x0
        assert tok.bbox.y1 > tok.bbox.y0
        assert tok.confidence > 0.5


@pytest.mark.asyncio
async def test_docling_handwriting_scan_routing(tmp_path):
    """Verify DoclingAdapter routes handwritten image files to the handwriting OCR provider."""
    img_path = tmp_path / "handwritten_sample.png"
    img = Image.new("RGB", (600, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 40), "Clinical Note: Follow-up required", fill=(0, 0, 0))
    draw.text((30, 100), "Action: Schedule blood test in 2 weeks", fill=(0, 0, 0))
    img.save(img_path)

    adapter = DoclingAdapter()
    canon_doc = await adapter.extract(
        document_id="test_doc_handwriting_01",
        file_path=img_path,
        mime_type="image/png",
        metadata={"ocr_engine": "handwriting"},
    )

    assert canon_doc is not None
    assert len(canon_doc.elements) >= 2
    all_text = " ".join(e.text for e in canon_doc.elements)
    assert "Clinical Note" in all_text or "Schedule" in all_text or "Follow-up" in all_text
    for elem in canon_doc.elements:
        assert elem.bbox.x1 > elem.bbox.x0
        assert elem.bbox.y1 > elem.bbox.y0
