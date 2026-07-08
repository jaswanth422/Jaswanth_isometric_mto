"""
Mock extraction provider.

Used whenever no Gemini API key is configured (or MODEL_PROVIDER=mock), so
the entire app — upload, table, CSV export — works end-to-end without any
credentials. Returns a realistic, hand-built MTO for a small sample line.
"""
from __future__ import annotations

from app.models import CoreMTOResponse


def extract_mock(image_bytes: bytes, filename: str) -> dict:
    """Returns a raw (pre-verification/normalization) extractor-shaped dict."""
    raw = CoreMTOResponse.model_validate(
        {
            "drawing_meta": {
                "drawing_no": "ISO-1501-01",
                "revision": "2",
                "line_number": '6"-P-1501-A1A-IH',
                "nps": '6"',
                "material_class": "A1A",
                "service": "Process",
            },
            "items": [
                {
                    "item_no": 1,
                    "category": "PIPE",
                    "description": "Pipe, Seamless, BE, ASME B36.10",
                    "size_nps": '6"',
                    "schedule_rating": "SCH 40",
                    "material_spec": "ASTM A106 Gr.B",
                    "end_type": "BW",
                    "quantity": 1,
                    "unit": "M",
                    "length_m": 12.45,
                    "confidence": 0.9,
                    "remarks": None,
                },
                {
                    "item_no": 2,
                    "category": "FITTING",
                    "description": "Elbow 90 Deg LR, BW, ASME B16.9",
                    "size_nps": '6"',
                    "schedule_rating": "SCH 40",
                    "material_spec": "ASTM A234 WPB",
                    "end_type": "BW",
                    "quantity": 4,
                    "unit": "EA",
                    "length_m": None,
                    "confidence": 0.85,
                    "remarks": None,
                },
                {
                    "item_no": 3,
                    "category": "FLANGE",
                    "description": "Weld Neck Flange, CL150, ASME B16.5",
                    "size_nps": '6"',
                    "schedule_rating": "CL150",
                    "material_spec": "ASTM A105",
                    "end_type": "BW",
                    "quantity": 2,
                    "unit": "EA",
                    "length_m": None,
                    "confidence": 0.8,
                    "remarks": None,
                },
                {
                    "item_no": 4,
                    "category": "VALVE",
                    "description": "Gate Valve, Flanged, CL150",
                    "size_nps": '6"',
                    "schedule_rating": "CL150",
                    "material_spec": "ASTM A216 WCB",
                    "end_type": "FLGD",
                    "quantity": 1,
                    "unit": "EA",
                    "length_m": None,
                    "confidence": 0.75,
                    "remarks": "Bowtie symbol partially obscured near tag",
                },
                {
                    "item_no": 5,
                    "category": "SUPPORT",
                    "description": "Pipe Support Shoe / Guide",
                    "size_nps": '6"',
                    "schedule_rating": None,
                    "material_spec": "CS",
                    "end_type": None,
                    "quantity": 1,
                    "unit": "EA",
                    "length_m": None,
                    "confidence": 0.62,
                    "remarks": "Illustrative support callout",
                },
                {
                    "item_no": 6,
                    "category": "INSTRUMENTATION",
                    "description": "Pressure Tapping / Instrument Connection",
                    "size_nps": '6"',
                    "schedule_rating": None,
                    "material_spec": "SS316",
                    "end_type": "SW",
                    "quantity": 1,
                    "unit": "EA",
                    "length_m": None,
                    "confidence": 0.6,
                    "remarks": "Illustrative instrument connection",
                },
            ],
        }
    )
    payload = raw.model_dump()
    payload["_source_filename"] = filename
    return payload
