import pytest
from pydantic import ValidationError

from app.models import CoreMTOResponse, DrawingMeta, MTOItem, MTOResponse, SECTION_34_MTO_EXAMPLE


def test_valid_mto_item():
    item = MTOItem(
        item_no=1,
        category="PIPE",
        description="Pipe, Seamless, BE",
        quantity=1,
        unit="M",
        length_m=12.45,
    )
    assert item.category == "PIPE"
    assert item.verification_status == "unverified"


def test_invalid_category_rejected():
    with pytest.raises(ValidationError):
        MTOItem(
            item_no=1,
            category="NOT_A_CATEGORY",
            description="bad item",
            quantity=1,
            unit="EA",
        )


def test_negative_quantity_rejected():
    with pytest.raises(ValidationError):
        MTOItem(
            item_no=1,
            category="VALVE",
            description="Gate valve",
            quantity=-1,
            unit="EA",
        )


def test_confidence_bounds():
    with pytest.raises(ValidationError):
        MTOItem(
            item_no=1,
            category="VALVE",
            description="Gate valve",
            quantity=1,
            unit="EA",
            confidence=1.5,
        )


def test_mto_response_defaults():
    response = MTOResponse()
    assert response.items == []
    assert response.mock is False
    assert isinstance(response.drawing_meta, DrawingMeta)


def test_section_34_example_validates_as_core_schema():
    response = CoreMTOResponse(**SECTION_34_MTO_EXAMPLE)
    assert response.drawing_meta.line_number == '6"-P-1501-A1A-IH'
    assert len(response.items) == 2
    assert response.summary.field_welds == 1


def test_api_response_extends_core_schema_without_breaking_it():
    response = MTOResponse(
        drawing_meta=SECTION_34_MTO_EXAMPLE["drawing_meta"],
        items=[{**SECTION_34_MTO_EXAMPLE["items"][0], "source_page": 1}],
        summary=SECTION_34_MTO_EXAMPLE["summary"],
        needs_review=[1],
        provider="mock",
        mock=True,
    )
    payload = response.model_dump()
    assert set(["drawing_meta", "items", "summary"]).issubset(payload)
    assert payload["items"][0]["source_page"] == 1
