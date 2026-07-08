"""
Orchestrates the four pipeline stages end-to-end:

  preprocess -> Extractor (Gemini or mock) -> Reader (OCR)
             -> Verifier (reconcile) -> Normalizer (units, derive, summarize)

If the Gemini call fails for any reason (bad key, timeout, malformed JSON),
we log the failure and fall back to the mock provider so the request never
raises a 500 on the documented happy path.
"""
from __future__ import annotations

import io
import logging
import time

from PIL import Image

from app.config import GEMINI_FAILURE_COOLDOWN_SECONDS, provider_context
from app.models import CoreMTOResponse, MTOResponse
from app.pipeline.mock_provider import extract_mock
from app.pipeline.ocr_reader import read_drawing
from app.pipeline.verifier import verify
from app.pipeline.normalizer import normalize

logger = logging.getLogger("mto_pipeline")
_gemini_unavailable_until = 0.0
_gemini_unavailable_reason: str | None = None


def _gemini_circuit_open() -> bool:
    return time.monotonic() < _gemini_unavailable_until


def _summarize_exception(exc: Exception) -> str:
    summary = " ".join(str(exc).split())
    return summary[:200] if len(summary) > 200 else summary


def _effective_provider(requested_provider: str, base_mock_reason: str | None) -> tuple[str, str | None, str | None]:
    if requested_provider != "gemini":
        return "mock", base_mock_reason, None
    if _gemini_circuit_open():
        logger.info("Gemini cooldown is active; using mock provider for this upload.")
        return "mock", "gemini_cooldown", _gemini_unavailable_reason
    return "gemini", None, None


def _mark_gemini_unhealthy(exc: Exception) -> None:
    global _gemini_unavailable_reason, _gemini_unavailable_until
    _gemini_unavailable_reason = _summarize_exception(exc)
    _gemini_unavailable_until = time.monotonic() + GEMINI_FAILURE_COOLDOWN_SECONDS
    logger.warning(
        "Gemini extraction failed (%s); using mock provider for %s seconds.",
        exc,
        GEMINI_FAILURE_COOLDOWN_SECONDS,
    )


def _pdf_to_image_pages(file_bytes: bytes) -> list[bytes]:
    """Render all PDF pages to PNG bytes."""
    try:
        from pdf2image import convert_from_bytes

        rendered_pages = convert_from_bytes(file_bytes, dpi=180)
        page_images: list[bytes] = []
        for page in rendered_pages:
            buf = io.BytesIO()
            page.save(buf, format="PNG")
            page_images.append(buf.getvalue())
        return page_images
    except Exception as exc:  # noqa: BLE001 - Poppler is optional; fall back cleanly.
        logger.warning("pdf2image rendering failed (%s); retrying with PyMuPDF.", exc)

    try:
        import fitz

        document = fitz.open(stream=file_bytes, filetype="pdf")
        page_images: list[bytes] = []
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(180 / 72, 180 / 72), alpha=False)
            page_images.append(pixmap.tobytes("png"))
        return page_images
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Unable to render PDF page to an image.") from exc


def _pdf_to_image_bytes(file_bytes: bytes) -> bytes:
    """Backward-compatible helper used by tests; returns the first rendered page."""
    pages = _pdf_to_image_pages(file_bytes)
    if not pages:
        raise RuntimeError("Unable to render PDF page to an image.")
    return pages[0]


def _normalize_image(file_bytes: bytes) -> bytes:
    # Re-encode through Pillow to normalize format/orientation and cap size.
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    max_dim = 2000
    if max(image.size) > max_dim:
        image.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _merge_ocr_results(target: dict, source: dict) -> None:
    target["has_bom"] = target.get("has_bom", False) or source.get("has_bom", False)
    target["field_welds"] = int(target.get("field_welds", 0)) + int(source.get("field_welds", 0))
    target["supports"] = int(target.get("supports", 0)) + int(source.get("supports", 0))
    target["instrumentation"] = int(target.get("instrumentation", 0)) + int(source.get("instrumentation", 0))

    merged_counts = target.setdefault("category_counts", {})
    for category, count in source.get("category_counts", {}).items():
        merged_counts[category] = merged_counts.get(category, 0) + count


def _extract_page(image_bytes: bytes, provider: str, filename: str) -> tuple[dict, bool, str | None, str | None]:
    if provider == "gemini":
        try:
            from app.pipeline.gemini_provider import extract_gemini

            raw = extract_gemini(image_bytes, "image/png", filename)
            return CoreMTOResponse.model_validate(raw).model_dump(), False, None, None
        except Exception as exc:  # noqa: BLE001 - deliberate broad catch, documented fallback
            _mark_gemini_unhealthy(exc)
            return extract_mock(image_bytes, filename), True, "gemini_error", _summarize_exception(exc)

    return extract_mock(image_bytes, filename), True, None, None


def run_pipeline(file_bytes: bytes, content_type: str, filename: str) -> MTOResponse:
    requested_provider, base_mock_reason = provider_context()
    provider, mock_reason, mock_details = _effective_provider(requested_provider, base_mock_reason)

    if content_type == "application/pdf":
        page_images = _pdf_to_image_pages(file_bytes)
        if not page_images:
            raise RuntimeError("No PDF pages could be rendered.")

        all_items: list[dict] = []
        merged_meta: dict = {}
        best_meta: dict = {}
        best_meta_score = -1
        merged_ocr: dict = {
            "has_bom": False,
            "category_counts": {},
            "field_welds": 0,
            "supports": 0,
            "instrumentation": 0,
            "raw_text": "",
        }
        next_item_no = 1
        used_mock = provider == "mock"

        for page_index, page_image in enumerate(page_images, start=1):
            raw, page_used_mock, page_mock_reason, page_mock_details = _extract_page(
                page_image, provider, f"{filename}-page-{page_index}"
            )
            used_mock = used_mock or page_used_mock
            if page_used_mock:
                provider = "mock"
                if page_mock_reason:
                    mock_reason = page_mock_reason
                if page_mock_details:
                    mock_details = page_mock_details

            # Collect and merge drawing_meta across pages. Prefer the page
            # with the most non-empty fields and a BOM presence.
            raw_meta = raw.get("drawing_meta", {}) or {}
            # merge non-empty fields into merged_meta (fill-first strategy)
            for k, v in raw_meta.items():
                if v and not merged_meta.get(k):
                    merged_meta[k] = v

            # score this page's meta: count non-empty fields + bonus if BOM
            page_meta_score = sum(1 for v in raw_meta.values() if v)
            page_ocr = read_drawing(page_image)
            # Prefer pages that contain a BOM (more likely to have correct title block)
            if page_ocr.get("has_bom"):
                page_meta_score += 5

            if page_meta_score > best_meta_score:
                best_meta_score = page_meta_score
                best_meta = raw_meta
            # merge ocr results
            _merge_ocr_results(merged_ocr, page_ocr)

            for item in raw.get("items", []):
                item["item_no"] = next_item_no
                item["source_page"] = page_index
                next_item_no += 1
                all_items.append(item)

        # Final merged_meta: prefer best_meta values first, then fill missing
        final_meta = dict(best_meta or {})
        for k, v in merged_meta.items():
            if v and not final_meta.get(k):
                final_meta[k] = v

        verified_items = verify(all_items, merged_ocr)
        response = normalize(final_meta, verified_items, merged_ocr)
        response.mock = used_mock
        response.provider = "mock" if used_mock else "gemini"
        response.mock_reason = mock_reason if used_mock else None
        response.mock_details = mock_details if used_mock else None
        return response

    image_bytes = _normalize_image(file_bytes)
    raw, used_mock, page_mock_reason, page_mock_details = _extract_page(image_bytes, provider, filename)
    if used_mock:
        mock_reason = page_mock_reason or mock_reason
        mock_details = page_mock_details or mock_details

    raw_meta = raw.get("drawing_meta", {})
    raw_items = raw.get("items", [])
    ocr_result = read_drawing(image_bytes)
    verified_items = verify(raw_items, ocr_result)

    response = normalize(raw_meta, verified_items, ocr_result)
    response.mock = used_mock
    response.provider = "mock" if used_mock else "gemini"
    response.mock_reason = mock_reason if used_mock else None
    response.mock_details = mock_details if used_mock else None
    return response
