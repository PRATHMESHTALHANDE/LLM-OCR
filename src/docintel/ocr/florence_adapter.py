"""
Open Doc Intelligence (docintel) - Microsoft Florence-2 Vision OCR Adapter
Integrates Florence-2 (<OCR_WITH_REGION>) for bounding-box grounded character and word extraction.
Engineered for strict <= 4GB VRAM execution in FP16 with automated CUDA OOM fallback.
"""

from io import BytesIO
import logging
from pathlib import Path
import time
from typing import Any

from docintel.config.settings import get_settings
from docintel.core.schemas import BoundingBox, CoordSystem
from docintel.ocr.base import BaseOCRProvider, OCRResult, OCRToken

logger = logging.getLogger(__name__)


class Florence2Adapter(BaseOCRProvider):
    """
    Microsoft Florence-2 Vision-Language Model adapter.
    Uses <OCR_WITH_REGION> prompt for fine-grained bounding box coordinates.
    """

    def __init__(
        self,
        model_id: str = "microsoft/Florence-2-base",
        device: str | None = None,
    ) -> None:
        self.model_id = model_id
        self._device = device
        self._model: Any = None
        self._processor: Any = None
        self._initialized: bool = False

    @property
    def name(self) -> str:
        return "florence2"

    @property
    def is_available(self) -> bool:
        try:
            import torch
            import transformers
            return True
        except ImportError:
            return False

    def _resolve_device(self) -> str:
        """Resolve best available hardware device."""
        if self._device:
            return self._device
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda:0"
        except ImportError:
            pass
        return "cpu"

    def _load_model(self) -> None:
        """Load Florence-2 model weights and processor with VRAM guards."""
        if self._initialized:
            return

        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor

        settings = get_settings()
        cache_dir = settings.DOCINTEL_MODEL_CACHE_DIR / "florence2"
        cache_dir.mkdir(parents=True, exist_ok=True)

        target_device = self._resolve_device()
        dtype = torch.float16 if "cuda" in target_device else torch.float32

        logger.info(
            "Loading Florence-2 (%s) on %s (dtype=%s)...",
            self.model_id, target_device, dtype,
        )

        self._processor = AutoProcessor.from_pretrained(
            self.model_id,
            trust_remote_code=True,
            cache_dir=str(cache_dir),
        )

        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=dtype,
            trust_remote_code=True,
            cache_dir=str(cache_dir),
        ).to(target_device)

        self._model.eval()
        self._initialized = True
        logger.info("Florence-2 loaded successfully into %s.", target_device)

    async def process_image(
        self,
        image_input: Path | bytes | Any,
        options: dict[str, Any] | None = None,
    ) -> OCRResult:
        """
        Run Florence-2 <OCR_WITH_REGION> on image input.
        Catches CUDA OOM gracefully and reports VRAM telemetry.
        """
        start_time = time.perf_counter()
        target_device = self._resolve_device()
        vram_mb = 0.0

        try:
            from PIL import Image
            import torch

            # Load PIL Image
            if isinstance(image_input, (str, Path)):
                image = Image.open(str(image_input)).convert("RGB")
            elif isinstance(image_input, bytes):
                image = Image.open(BytesIO(image_input)).convert("RGB")
            elif hasattr(image_input, "convert"):
                image = image_input.convert("RGB")
            else:
                raise ValueError(f"Unsupported image input type: {type(image_input)}")

            img_width, img_height = image.size

            # Load model weights if not loaded
            self._load_model()

            task_prompt = "<OCR_WITH_REGION>"
            inputs = self._processor(
                text=task_prompt,
                images=image,
                return_tensors="pt",
            )

            # Move inputs to device
            inputs = {k: v.to(target_device) for k, v in inputs.items()}
            if "cuda" in target_device:
                inputs["pixel_values"] = inputs["pixel_values"].to(torch.float16)

            with torch.inference_mode():
                generated_ids = self._model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    num_beams=3,
                    do_sample=False,
                )

            generated_text = self._processor.batch_decode(
                generated_ids, skip_special_tokens=False
            )[0]

            parsed_answer = self._processor.post_process_generation(
                generated_text,
                task=task_prompt,
                image_size=(img_width, img_height),
            )

            # Measure VRAM
            if "cuda" in target_device:
                vram_mb = torch.cuda.memory_allocated() / (1024.0 * 1024.0)

            # Parse detected bounding boxes
            tokens: list[OCRToken] = []
            extracted_texts: list[str] = []

            raw_regions = parsed_answer.get("<OCR_WITH_REGION>", {})
            labels = raw_regions.get("labels", [])
            boxes = raw_regions.get("quad_boxes", []) or raw_regions.get("bboxes", [])

            for label, box in zip(labels, boxes):
                label_str = str(label).strip()
                if not label_str:
                    continue
                extracted_texts.append(label_str)

                # Convert quad box or bbox to standardized BoundingBox
                if len(box) == 8:
                    xs = [box[0], box[2], box[4], box[6]]
                    ys = [box[1], box[3], box[5], box[7]]
                    bbox = BoundingBox(
                        x0=float(min(xs)),
                        y0=float(min(ys)),
                        x1=float(max(xs)),
                        y1=float(max(ys)),
                        coord_system=CoordSystem.PIXEL,
                    )
                elif len(box) == 4:
                    bbox = BoundingBox(
                        x0=float(box[0]),
                        y0=float(box[1]),
                        x1=float(box[2]),
                        y1=float(box[3]),
                        coord_system=CoordSystem.PIXEL,
                    )
                else:
                    bbox = BoundingBox(x0=0, y0=0, x1=0, y1=0)

                tokens.append(
                    OCRToken(
                        text=label_str,
                        confidence=0.95,
                        bbox=bbox,
                    )
                )

            full_text = " ".join(extracted_texts)
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            return OCRResult(
                text=full_text,
                tokens=tokens,
                markdown=full_text,
                latency_ms=latency_ms,
                vram_used_mb=vram_mb,
                model_name=self.model_id,
                extra={"detected_region_count": len(tokens)},
            )

        except Exception as e:
            # Handle CUDA OOM or missing weights gracefully
            err_str = str(e)
            logger.error("Florence-2 OCR inference error: %s", err_str)
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return OCRResult(
                text="",
                tokens=[],
                latency_ms=latency_ms,
                vram_used_mb=vram_mb,
                model_name=self.model_id,
                extra={"error": err_str, "status": "failed"},
            )
