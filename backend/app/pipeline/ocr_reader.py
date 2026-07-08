"""
Reader Agent.

Runs OCR over the full drawing and looks specifically for:
  - title-block fields (line number, drawing number, revision) via regex
  - rough per-category item counts, by keyword-matching category names that
    typically appear in a printed BOM table (e.g. "ELBOW", "GATE VALVE")

This is intentionally a *different* technique from the Extractor (OCR vs.
vision-LLM symbol reading), so its errors are largely uncorrelated with the
Extractor's — that independence is what makes the Verifier's cross-check
meaningful rather than redundant.

If OCR finds no BOM-like text at all (e.g. a hand-drawn iso with no table),
this returns has_bom=False and the Verifier skips reconciliation for that
drawing rather than fabricating a comparison.
"""
from __future__ import annotations

import io
import re

from PIL import Image

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except Exception:  # pragma: no cover - tesseract binary may not be installed
    TESSERACT_AVAILABLE = False

LINE_NUMBER_RE = re.compile(r'\b\d{1,2}"?-[A-Z]{1,3}-\d{3,5}-[A-Z0-9]{2,5}(?:-[A-Z0-9]{1,4})?\b')
DRAWING_NO_RE = re.compile(r'\b(?:ISO|DWG)[-\s]?[A-Z0-9\-]{4,}\b', re.IGNORECASE)
REVISION_RE = re.compile(r'\bREV(?:ISION)?\s*[:\-]?\s*([A-Z0-9]{1,3})\b', re.IGNORECASE)
FIELD_WELD_RE = re.compile(r'\b(?:FW|FIELD\s+WELD)\b', re.IGNORECASE)
SUPPORT_RE = re.compile(r'\b(?:SUPPORT|SHOE|GUIDE|ANCHOR|HANGER|PS-\d+)\b', re.IGNORECASE)
INSTRUMENT_RE = re.compile(r'\b(?:INSTRUMENT(?:ATION)?|PRESSURE\s+TAPPING|TEMP(?:ERATURE)?\s+TAPPING|PT\b|TT\b)\b', re.IGNORECASE)

CATEGORY_KEYWORDS = {
    "FITTING": ["ELBOW", "TEE", "REDUCER", "COUPLING", "UNION", "OLET", "CAP"],
    "FLANGE": ["FLANGE", "WELD NECK", "BLIND FLANGE", "SLIP-ON", "SLIP ON"],
    "VALVE": ["GATE VALVE", "GLOBE VALVE", "CHECK VALVE", "BALL VALVE", "BUTTERFLY VALVE", "VALVE"],
    "GASKET": ["GASKET"],
    "BOLT": ["STUD BOLT", "BOLT"],
}


def read_drawing(image_bytes: bytes) -> dict:
    """Returns OCR-derived title-block fields and rough per-category counts."""
    result = {
        "has_bom": False,
        "drawing_no": None,
        "revision": None,
        "line_number": None,
        "field_welds": 0,
        "supports": 0,
        "instrumentation": 0,
        "category_counts": {},
        "raw_text": "",
    }

    if not TESSERACT_AVAILABLE:
        return result

    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Full OCR text for fallbacks and non-BOM signals
        full_text = pytesseract.image_to_string(image)
    except Exception:
        return result

    result["raw_text"] = full_text
    text_upper = full_text.upper()

    # Title-block detection: prefer text in the bottom 20% of the image to
    # avoid picking up incidental occurrences elsewhere on the sheet.
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except Exception:
        data = None

    # Extract bottom-region text for title-block regexes
    title_text = ""
    if data:
        height = image.size[1]
        bottom_threshold = int(height * 0.8)
        parts = []
        for i, top in enumerate(data["top"]):
            try:
                top_val = int(top)
            except Exception:
                continue
            if top_val >= bottom_threshold:
                word = data["text"][i]
                if word and word.strip():
                    parts.append(word)
        title_text = " ".join(parts)

    # Fallback to whole text if bottom-region sparse
    title_search_text = title_text if title_text.strip() else full_text

    line_match = LINE_NUMBER_RE.search(title_search_text)
    if line_match:
        result["line_number"] = line_match.group(0)

    dwg_match = DRAWING_NO_RE.search(title_search_text)
    if dwg_match:
        result["drawing_no"] = dwg_match.group(0)

    rev_match = REVISION_RE.search(title_search_text)
    if rev_match:
        result["revision"] = rev_match.group(1)

    # Field welds/supports/instrumentation we keep from whole image text
    result["field_welds"] = len(FIELD_WELD_RE.findall(text_upper))
    result["supports"] = len(SUPPORT_RE.findall(text_upper))
    result["instrumentation"] = len(INSTRUMENT_RE.findall(text_upper))

    # Attempt to localize BOM table: look for blocks/lines containing BOM headers
    bom_indicators = ["BILL OF MATERIAL", "BILL OF MATERIALS", "B.O.M", "BOM", "ITEM", "QTY", "QUANTITY", "DESCRIPTION"]
    bom_text = ""
    if data:
        # group by block_num to get contiguous blocks
        block_texts: dict[int, list[str]] = {}
        for i, block_num in enumerate(data.get("block_num", [])):
            try:
                b = int(block_num)
            except Exception:
                continue
            word = data["text"][i]
            if word and word.strip():
                block_texts.setdefault(b, []).append(word)

        # find blocks that look like BOM table headers
        for bnum, words in block_texts.items():
            joined = " ".join(words).upper()
            if any(ind in joined for ind in bom_indicators):
                bom_text = joined
                break

    # If we found a BOM block, count keywords only in that block; otherwise use full text
    count_source = bom_text if bom_text else text_upper

    counts: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        total = 0
        for kw in keywords:
            total += len(re.findall(re.escape(kw), count_source))
        if total > 0:
            counts[category] = total

    # incorporate supports/instrumentation counts if present
    if result["supports"] > 0:
        counts["SUPPORT"] = max(counts.get("SUPPORT", 0), result["supports"])
    if result["instrumentation"] > 0:
        counts["INSTRUMENTATION"] = max(counts.get("INSTRUMENTATION", 0), result["instrumentation"])

    result["category_counts"] = counts
    result["has_bom"] = bool(counts) or bool(bom_text) or any([result["line_number"], result["drawing_no"]])

    return result
