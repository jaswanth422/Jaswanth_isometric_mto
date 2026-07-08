"""
Verifier Agent.

Deterministic reconciliation function (not an LLM call) that cross-checks
the Extractor's per-category item counts against the Reader's OCR'd BOM
counts. Where they agree, confidence is left as-is (or nudged up slightly).
Where they disagree, every item in that category is flagged
"conflict" with both counts recorded in `remarks`, rather than one source
being silently trusted over the other.

This is the core "why trust one signal" design decision of this submission.
"""
from __future__ import annotations


def _extractor_counts(items: list[dict]) -> dict[str, float]:
    counts: dict[str, float] = {}
    for item in items:
        cat = item.get("category")
        qty = item.get("quantity") or 0
        if cat == "PIPE":
            continue  # pipe is reconciled by length elsewhere, not count
        counts[cat] = counts.get(cat, 0) + qty
    return counts


def verify(items: list[dict], ocr_result: dict) -> list[dict]:
    if not ocr_result.get("has_bom"):
        for item in items:
            item["verification_status"] = "no_bom_available"
        return items

    ext_counts = _extractor_counts(items)
    ocr_counts = ocr_result.get("category_counts", {})

    conflicts: dict[str, tuple[float, int]] = {}
    for category, ocr_count in ocr_counts.items():
        ext_count = ext_counts.get(category, 0)
        # Allow off-by-one tolerance: OCR keyword counting over-counts easily
        # (e.g. "VALVE" matching inside "GATE VALVE" too).
        if abs(ext_count - ocr_count) > 1:
            conflicts[category] = (ext_count, ocr_count)

    for item in items:
        cat = item.get("category")
        if cat == "PIPE":
            item["verification_status"] = "unverified"
            continue
        if cat in conflicts:
            ext_count, ocr_count = conflicts[cat]
            item["verification_status"] = "conflict"
            note = f"Extractor found {ext_count:g} {cat.lower()}(s); BOM/OCR text suggests {ocr_count:g}."
            item["remarks"] = f"{item.get('remarks') or ''} {note}".strip()
        elif cat in ocr_counts:
            item["verification_status"] = "match"
        else:
            item["verification_status"] = "unverified"

    return items
