"""
The extraction prompt and JSON schema sent to Gemini's vision endpoint.

Kept as plain Python so it's easy to read, version, and reference from the
README — this is graded directly as part of "AI pipeline design".
"""

EXTRACTION_PROMPT = """You are a piping engineer's assistant reading a piping isometric drawing
("iso"). Extract a Material Take-Off (MTO) as structured JSON.

Domain rules you must follow:
- Categorize every item as one of: PIPE, FITTING, FLANGE, VALVE, GASKET, BOLT, SUPPORT, INSTRUMENTATION.
- Quantify PIPE by total cut length in metres (unit "M"). Quantify every other
  category by count (unit "EA", "NO", or "SET").
- Fittings include elbows (90/45 deg, LR/SR), tees, reducers, caps, couplings,
  unions, and olets. Use the symbol shape and position in the routing to identify them.
- Flanges (weld-neck, slip-on, blind, socket-weld) appear as short perpendicular
  ticks on the pipe line, usually near a valve or equipment connection.
- Valves are drawn as a "bowtie" (two triangles): gate (plain), globe (solid
  centre dot), check (flap), ball (circle), butterfly. Report the valve type
  if the symbol makes it distinguishable, otherwise report "Valve (type unclear)".
- Do NOT invent gaskets or bolt sets per item unless you can see them as
  distinct callouts — the pipeline's Normalizer stage derives these
  automatically from flanged joints, so only report what you can actually see.
- Read the title block for: drawing number, revision, line number (e.g.
  6"-P-1501-A1A-IH), NPS, material class, and service.
- For every item, include a confidence score from 0 to 1 reflecting how
  legible/unambiguous that specific item was on the drawing. Be honest — a
  low score on a cluttered or unclear region is more useful than a
  falsely-confident guess.
- If a field cannot be determined, return null for it rather than guessing.
- Include a top-level `summary` object with totals for the extracted items and field welds.

Return ONLY JSON matching the provided schema. No prose, no markdown fences.
"""

# Passed to Gemini as response_schema (via google-generativeai's GenerationConfig).
# This captures the core Section 3.4-style extractor payload only; pipeline
# enrichment like `source_page`, `verification_status`, and `needs_review` is
# added later by deterministic backend stages.
MTO_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "drawing_meta": {
            "type": "object",
            "properties": {
                "drawing_no": {"type": "string", "nullable": True},
                "revision": {"type": "string", "nullable": True},
                "line_number": {"type": "string", "nullable": True},
                "nps": {"type": "string", "nullable": True},
                "material_class": {"type": "string", "nullable": True},
                "service": {"type": "string", "nullable": True},
            },
        },
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_no": {"type": "integer"},
                    "category": {
                        "type": "string",
                        "enum": ["PIPE", "FITTING", "FLANGE", "VALVE", "GASKET", "BOLT", "SUPPORT", "INSTRUMENTATION"],
                    },
                    "description": {"type": "string"},
                    "size_nps": {"type": "string", "nullable": True},
                    "schedule_rating": {"type": "string", "nullable": True},
                    "material_spec": {"type": "string", "nullable": True},
                    "end_type": {"type": "string", "nullable": True},
                    "quantity": {"type": "number"},
                    "unit": {"type": "string", "enum": ["M", "EA", "NO", "SET"]},
                    "length_m": {"type": "number", "nullable": True},
                    "confidence": {"type": "number"},
                    "remarks": {"type": "string", "nullable": True},
                },
                "required": ["item_no", "category", "description", "quantity", "unit"],
            },
        },
        "summary": {
            "type": "object",
            "properties": {
                "total_pipe_length_m": {"type": "number"},
                "fittings": {"type": "integer"},
                "flanges": {"type": "integer"},
                "valves": {"type": "integer"},
                "gaskets": {"type": "integer"},
                "bolt_sets": {"type": "integer"},
                "supports": {"type": "integer"},
                "instrumentation_connections": {"type": "integer"},
                "field_welds": {"type": "integer"},
            },
            "required": [
                "total_pipe_length_m",
                "fittings",
                "flanges",
                "valves",
                "gaskets",
                "bolt_sets",
                "supports",
                "instrumentation_connections",
                "field_welds",
            ],
        },
    },
    "required": ["drawing_meta", "items", "summary"],
}
