"""
Normalizer Agent.

Deterministic post-processing:
  - normalizes units (nothing fancy needed here since the schema already
    enforces M/EA/NO/SET, but this is where mm->m conversions would live if
    a drawing reports lengths in mm)
  - derives gasket + bolt sets per flanged joint if the Extractor didn't
    report them directly, tagging them `derived_from` so it's clear which
    rows were inferred rather than read off the drawing
  - computes summary totals
  - builds the `needs_review` list from low confidence / conflict items
"""
from __future__ import annotations

from app.models import MTOItem, MTOSummary, MTOResponse, DrawingMeta

CONFIDENCE_REVIEW_THRESHOLD = 0.6


def normalize(raw_meta: dict, items: list[dict], ocr_result: dict | None = None) -> MTOResponse:
    parsed_items = [MTOItem(**item) for item in items]
    ocr_result = ocr_result or {}
    default_source_page = min((i.source_page for i in parsed_items if i.source_page is not None), default=None)

    flange_count = sum(i.quantity for i in parsed_items if i.category == "FLANGE")

    has_gasket = any(i.category == "GASKET" for i in parsed_items)
    has_bolt = any(i.category == "BOLT" for i in parsed_items)

    next_item_no = max((i.item_no for i in parsed_items), default=0) + 1

    if flange_count > 0 and not has_gasket:
        parsed_items.append(
            MTOItem(
                item_no=next_item_no,
                category="GASKET",
                description="Spiral Wound Gasket, ASME B16.20",
                quantity=flange_count,
                unit="EA",
                confidence=None,
                derived_from="1 gasket per flanged joint (ASME B16.20 convention) - not directly extracted",
                source_page=default_source_page,
                verification_status="unverified",
            )
        )
        next_item_no += 1

    support_count = int(ocr_result.get("supports", 0))
    if support_count > 0 and not any(i.category == "SUPPORT" for i in parsed_items):
        parsed_items.append(
            MTOItem(
                item_no=next_item_no,
                category="SUPPORT",
                description="Pipe Support / Shoe / Guide / Anchor / Hanger",
                quantity=support_count,
                unit="EA",
                confidence=None,
                derived_from="OCR-detected support keywords on the drawing",
                source_page=default_source_page,
                verification_status="unverified",
            )
        )
        next_item_no += 1

    instrumentation_count = int(ocr_result.get("instrumentation", 0))
    if instrumentation_count > 0 and not any(i.category == "INSTRUMENTATION" for i in parsed_items):
        parsed_items.append(
            MTOItem(
                item_no=next_item_no,
                category="INSTRUMENTATION",
                description="Instrumentation Connection / Tapping",
                quantity=instrumentation_count,
                unit="EA",
                confidence=None,
                derived_from="OCR-detected instrumentation keywords on the drawing",
                source_page=default_source_page,
                verification_status="unverified",
            )
        )
        next_item_no += 1

    if flange_count > 0 and not has_bolt:
        parsed_items.append(
            MTOItem(
                item_no=next_item_no,
                category="BOLT",
                description="Stud Bolts with Nuts, ASTM A193 B7 / A194 2H",
                quantity=flange_count,
                unit="SET",
                confidence=None,
                derived_from="1 bolt set per flanged joint - not directly extracted",
                source_page=default_source_page,
                verification_status="unverified",
            )
        )

    summary = MTOSummary(
        total_pipe_length_m=round(
            sum(i.length_m or 0 for i in parsed_items if i.category == "PIPE"), 2
        ),
        fittings=int(sum(i.quantity for i in parsed_items if i.category == "FITTING")),
        flanges=int(flange_count),
        valves=int(sum(i.quantity for i in parsed_items if i.category == "VALVE")),
        gaskets=int(sum(i.quantity for i in parsed_items if i.category == "GASKET")),
        bolt_sets=int(sum(i.quantity for i in parsed_items if i.category == "BOLT")),
        supports=int(sum(i.quantity for i in parsed_items if i.category == "SUPPORT")),
        instrumentation_connections=int(sum(i.quantity for i in parsed_items if i.category == "INSTRUMENTATION")),
        field_welds=int(ocr_result.get("field_welds", 0)),
    )

    needs_review = [
        i.item_no
        for i in parsed_items
        if i.verification_status == "conflict"
        or (i.confidence is not None and i.confidence < CONFIDENCE_REVIEW_THRESHOLD)
    ]

    meta = DrawingMeta(**{k: v for k, v in raw_meta.items() if k in DrawingMeta.model_fields})

    return MTOResponse(
        drawing_meta=meta,
        items=parsed_items,
        summary=summary,
        needs_review=needs_review,
    )
