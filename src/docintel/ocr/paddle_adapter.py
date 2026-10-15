"""
Open Doc Intelligence (docintel) - PaddleOCR CPU Adapter
Integrates PaddleOCR (PP-OCRv4) for low-latency, CPU-friendly text detection,
angle classification, and character recognition.
"""

from io import BytesIO
import logging
from pathlib import Path
import time
from typing import Any

from docintel.core.schemas import BoundingBox, CoordSystem
from docintel.ocr.base import BaseOCRProvider, OCRResult, OCRToken

logger = logging.getLogger(__name__)


class PaddleOCRAdapter(BaseOCRProvider):
    """Adapter for PaddleOCR CPU text detection and recognition."""

    def __init__(self, lang: str = "en", use_angle_cls: bool = True) -> None:
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self._ocr: Any = None
        self._initialized: bool = False

    @property
    def name(self) -> str:
        return "paddle"

    @property
    def is_available(self) -> bool:
        try:
            import paddleocr
            return True
        except ImportError:
            try:
                import rapidocr_onnxruntime
                return True
            except ImportError:
                return False

    def _init_ocr(self) -> None:
        """Lazily load PaddleOCR or RapidOCR engine."""
        if not self._initialized:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(
                    use_angle_cls=self.use_angle_cls,
                    lang=self.lang,
                    show_log=False,
                )
                self._is_rapid = False
                self._initialized = True
            except ImportError:
                try:
                    from rapidocr_onnxruntime import RapidOCR
                    self._ocr = RapidOCR()
                    self._is_rapid = True
                    self._initialized = True
                    logger.info("Using RapidOCR (PP-OCRv4 ONNX) engine for PaddleOCR provider.")
                except ImportError:
                    logger.warning("PaddleOCR and RapidOCR are not installed in the environment.")
                    self._ocr = None
                    self._initialized = True

    async def process_image(
        self,
        image_input: Path | bytes | Any,
        options: dict[str, Any] | None = None,
    ) -> OCRResult:
        start_time = time.perf_counter()
        self._init_ocr()

        if self._ocr is None:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return OCRResult(
                text="",
                tokens=[],
                latency_ms=latency_ms,
                model_name="paddle_ocr_cpu",
                extra={"error": "PaddleOCR library not available", "status": "unavailable"},
            )

        try:
            import numpy as np
            from PIL import Image

            if isinstance(image_input, (str, Path)):
                img = Image.open(str(image_input)).convert("RGB")
            elif isinstance(image_input, bytes):
                img = Image.open(BytesIO(image_input)).convert("RGB")
            elif hasattr(image_input, "convert"):
                img = image_input.convert("RGB")
            else:
                img = Image.fromarray(image_input).convert("RGB")

            img_np = np.array(img)
            tokens: list[OCRToken] = []
            extracted_lines: list[str] = []

            if getattr(self, "_is_rapid", False):
                ocr_results, _ = self._ocr(img_np)
                if ocr_results:
                    for line in ocr_results:
                        box_points, text, conf = line
                        xs = [pt[0] for pt in box_points]
                        ys = [pt[1] for pt in box_points]
                        bbox = BoundingBox(
                            x0=round(float(min(xs)), 2),
                            y0=round(float(min(ys)), 2),
                            x1=round(float(max(xs)), 2),
                            y1=round(float(max(ys)), 2),
                            coord_system=CoordSystem.PIXEL,
                        )
                        tokens.append(
                            OCRToken(
                                text=str(text).strip(),
                                confidence=round(float(conf), 3),
                                bbox=bbox,
                                polygon=[[float(p[0]), float(p[1])] for p in box_points],
                            )
                        )
                        extracted_lines.append(str(text).strip())
            else:
                result = self._ocr.ocr(img_np, cls=self.use_angle_cls)
                if result and result[0]:
                    for line in result[0]:
                        box_points, (text, conf) = line
                        xs = [pt[0] for pt in box_points]
                        ys = [pt[1] for pt in box_points]

                        bbox = BoundingBox(
                            x0=float(min(xs)),
                            y0=float(min(ys)),
                            x1=float(max(xs)),
                            y1=float(max(ys)),
                            coord_system=CoordSystem.PIXEL,
                        )

                        tokens.append(
                            OCRToken(
                                text=str(text),
                                confidence=float(conf),
                                bbox=bbox,
                                polygon=[[float(p[0]), float(p[1])] for p in box_points],
                            )
                        )
                        extracted_lines.append(str(text))

            full_text = "\n".join(extracted_lines)
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            return OCRResult(
                text=full_text,
                tokens=tokens,
                markdown=full_text,
                latency_ms=latency_ms,
                vram_used_mb=0.0,
                model_name="paddle_ocr_v4_cpu",
                extra={"line_count": len(extracted_lines)},
            )

        except Exception as e:
            logger.error("PaddleOCR execution failed: %s", e)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return OCRResult(
                text="",
                tokens=[],
                latency_ms=latency_ms,
                model_name="paddle_ocr_cpu",
                extra={"error": str(e), "status": "failed"},
            )
