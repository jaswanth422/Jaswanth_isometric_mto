"""
Extractor Agent: calls Gemini's vision API with a strict JSON schema so the
model's output is never hand-parsed from free text.

Any failure here (bad key, timeout, malformed response) is caught by the
caller (pipeline.py), which falls back to the mock provider rather than
crashing the request.
"""
from __future__ import annotations

import json

import google.generativeai as genai

from app.config import GEMINI_API_KEY, GEMINI_TIMEOUT_SECONDS
from app.pipeline.prompts import EXTRACTION_PROMPT, MTO_RESPONSE_SCHEMA

MODEL_NAME = "gemini-2.5-flash"


def extract_gemini(image_bytes: bytes, mime_type: str, filename: str) -> dict:
    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel(MODEL_NAME)

    response = model.generate_content(
        [
            {"mime_type": mime_type, "data": image_bytes},
            EXTRACTION_PROMPT,
        ],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=MTO_RESPONSE_SCHEMA,
        ),
        request_options={"timeout": GEMINI_TIMEOUT_SECONDS},
    )

    raw = json.loads(response.text)
    raw["_source_filename"] = filename
    return raw
