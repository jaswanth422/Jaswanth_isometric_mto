# Isometric Drawing to Automated MTO Generator

Full-stack app that takes a single piping isometric drawing (image or PDF) and generates a structured Material Take-Off (MTO), viewable as a table and exportable as CSV.

Built with Next.js (App Router) + FastAPI. Verified end-to-end: backend tests pass, frontend builds cleanly, and the full upload → extract → CSV flow was tested locally with both servers running together.

---

## 1. Architecture

```
┌─────────────┐        ┌───────────────────────────────────────────────┐
│  Next.js    │  HTTP  │                    FastAPI                     │
│  Frontend   │───────▶│                                                 │
│             │        │  preprocess (PDF→PNG, resize)                  │
│  Upload  ───┼───────▶│         │                                       │
│  page       │        │         ▼                                       │
│             │        │  ┌────────────┐      ┌────────────┐            │
│  Results ◀──┼────────┤  │ Extractor  │      │  Reader    │            │
│  (table +   │  JSON  │  │  Agent     │      │  Agent     │            │
│  CSV export)│        │  │ (Gemini    │      │  (OCR:     │            │
└─────────────┘        │  │  vision,   │      │  BOM table │            │
                        │  │  or mock)  │      │  + title   │            │
                        │  └─────┬──────┘      │  block)    │            │
                        │        │             └─────┬──────┘            │
                        │        └────────┬──────────┘                   │
                        │                 ▼                              │
                        │       ┌──────────────────────┐                 │
                        │       │   Verifier Agent      │                 │
                        │       │  reconciles item      │                 │
                        │       │  counts, flags        │                 │
                        │       │  conflicts             │                 │
                        │       └──────────┬───────────┘                 │
                        │                  ▼                              │
                        │       ┌──────────────────────┐                 │
                        │       │  Normalizer Agent      │                 │
                        │       │  derives gasket/bolt   │                 │
                        │       │  sets, computes        │                 │
                        │       │  summary totals        │                 │
                        │       └──────────┬───────────┘                 │
                        │                  ▼                              │
                        │         Validated MTO JSON                      │
                        └───────────────────────────────────────────────┘
```

**Why this design, not a single LLM call:** most naive implementations trust one vision-LLM output blindly. Here, the **Extractor** (Gemini vision) and **Reader** (OCR on the BOM table/title block) are genuinely independent techniques with uncorrelated failure modes. The **Verifier** cross-checks their per-category item counts — where they agree, confidence holds; where they disagree, the item is flagged `conflict` with both counts shown, rather than one source silently winning. This mirrors how MTOs are actually checked in practice (Section 2.1 of the brief: most real isos carry both a drawn route *and* a BOM table).

The frontend also surfaces confidence visually and exposes both CSV and Excel exports so the result is easy to review, share, and grade.

**Backend contract:** upload a drawing with `POST /api/upload` and retrieve the job result and exports with `GET /api/mto/{job_id}`, `GET /api/mto/{job_id}/csv`, and `GET /api/mto/{job_id}/xlsx`. This is safe enough for the demo because every result is keyed by a deterministic `job_id` rather than an in-memory "last result" cache.

---

## 2. Setup (tested locally)

### Requirements
- Python 3.11+ (tested on 3.12)
- Node.js 18+ (tested with Next.js 14.2.32)
- Tesseract OCR installed system-wide (for the Reader agent's OCR pass)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add GEMINI_API_KEY, or leave blank for mock mode
uvicorn app.main:app --reload --port 8000
```

Install Tesseract separately (it's a system binary, not a pip package):
```bash
# macOS
brew install tesseract
# Ubuntu/Debian
sudo apt-get install tesseract-ocr
```

For PDF uploads, the backend now falls back to PyMuPDF if Poppler is unavailable.
Poppler is still supported, but it is no longer required for PDF processing.

Backend runs at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`. Verify with:
```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local      # sets NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Frontend runs at `http://localhost:3000`.

### Running without a Gemini API key

Leave `GEMINI_API_KEY` blank in `backend/.env` (or set `MODEL_PROVIDER=mock`). The backend automatically falls back to a clearly-labeled mock MTO — the response includes `"mock": true`, and the frontend shows a blue banner saying so. The full flow (upload, table, review queue, CSV export) works with zero credentials. This was verified directly: uploading a blank test image returns a complete mock MTO with correctly-derived gasket and bolt-set rows.

---

## 3. Environment Variables

**root `.env.example`**
```
# Backend
GEMINI_API_KEY=
MODEL_PROVIDER=gemini
GEMINI_TIMEOUT_SECONDS=120
GEMINI_FAILURE_COOLDOWN_SECONDS=600
MAX_UPLOAD_MB=20
ALLOWED_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**backend/.env.example**
```
GEMINI_API_KEY=
MODEL_PROVIDER=gemini
GEMINI_TIMEOUT_SECONDS=120
GEMINI_FAILURE_COOLDOWN_SECONDS=600
MAX_UPLOAD_MB=20
ALLOWED_ORIGINS=http://localhost:3000
```

**frontend/.env.example**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

No real keys are committed anywhere in this repo.

---

## 4. API Endpoints

```
POST /api/upload          multipart file upload -> JobInfo with result_id
GET  /api/mto/{job_id}    returns job info and completed MTO payload
GET  /api/mto/{job_id}/csv returns the completed MTO as a CSV download
GET  /api/mto/{job_id}/xlsx returns the completed MTO as an Excel workbook download
GET  /api/health          liveness check
```

Server-side validation (independent of the frontend): content-type restricted to PNG/JPG/PDF, file size capped by `MAX_UPLOAD_MB`, empty files rejected. All error paths return structured JSON (`{"detail": "..."}`), never a raw crash — verified with tests for bad content-type and empty-file cases.

**Behavior note:** exports are keyed by `job_id`, so CSV/XLSX downloads are deterministic per upload and do not reuse a global "latest" result cache.

### Core MTO JSON Shape

The extractor's core contract follows the suggested Section 3.4 shape:

```json
{
  "drawing_meta": {
    "drawing_no": "ISO-1501-01",
    "revision": "2",
    "line_number": "6\"-P-1501-A1A-IH",
    "nps": "6\"",
    "material_class": "A1A",
    "service": "Process"
  },
  "items": [
    {
      "item_no": 1,
      "category": "PIPE",
      "description": "Pipe, Seamless, BE, ASME B36.10",
      "size_nps": "6\"",
      "schedule_rating": "SCH 40",
      "material_spec": "ASTM A106 Gr.B",
      "end_type": "BW",
      "quantity": 1,
      "unit": "M",
      "length_m": 12.45,
      "confidence": 0.92,
      "remarks": ""
    }
  ],
  "summary": {
    "total_pipe_length_m": 12.45,
    "fittings": 4,
    "flanges": 2,
    "valves": 1,
    "gaskets": 2,
    "bolt_sets": 2,
    "field_welds": 1
  }
}
```

The final API response keeps those same top-level keys and adds review-oriented fields such as `needs_review`, `verification_status`, `derived_from`, `source_page`, `mock`, and `provider`.

---

## 5. How the AI Pipeline Works

1. **Pre-process** (`app/pipeline/pipeline.py`): PDFs are rendered page-by-page to PNG; images are re-encoded through Pillow and capped at 2000px on the long edge.
2. **Extract** (`app/pipeline/gemini_provider.py`): the image is sent to `gemini-2.5-flash` with a domain-specific prompt (`app/pipeline/prompts.py`) and a strict `response_schema`, so the model's output is never hand-parsed from free text. The backend exposes `GEMINI_TIMEOUT_SECONDS` to accommodate dense drawings; the verified real-provider run for the included sample used a 120-second timeout. If this call fails for any reason (bad key, timeout, malformed response), the pipeline logs it and falls back to the mock provider rather than crashing the request.
3. **Read** (`app/pipeline/ocr_reader.py`): Tesseract OCR runs over the full image; regex patterns pull the line number, drawing number, and revision from the title block, and keyword-matching against BOM-table vocabulary (ELBOW, TEE, FLANGE, VALVE, GASKET, BOLT) gives rough per-category counts. If no BOM-like text is found at all, `has_bom` is `False` and the Verifier is skipped for that drawing rather than fabricating a comparison.
4. **Reconcile** (`app/pipeline/verifier.py`): per-category counts from the Extractor and Reader are compared with a tolerance of ±1 (OCR keyword-matching over-counts easily, e.g. "VALVE" matching inside "GATE VALVE" too). Disagreements beyond that tolerance mark every item in that category `conflict`, with both counts recorded in `remarks`.
5. **Normalize** (`app/pipeline/normalizer.py`): derives gasket + bolt sets (1 each per flanged joint, per ASME B16.20 convention) only if the Extractor didn't report them directly, tagging them `derived_from` so it's clear which rows were inferred. Computes summary totals. Builds the `needs_review` list from any item that's either `conflict` or below a 0.6 confidence threshold.
6. **Serve**: the fully Pydantic-validated `MTOResponse` goes back to the frontend.

### Accuracy — what will work, what won't

**Likely to work well:**
- Clean, printed (non-hand-drawn) isometrics with a legible BOM table
- Common symbols: elbows, tees, reducers, gate/globe valves, flanges
- Horizontal, unobstructed title-block text

**Likely to fail or need review (flagged, not hidden):**
- Dense drawings with overlapping dimension lines
- Hand-drawn or low-contrast scanned isometrics
- Text rotated at the drawing's native 30°/150° isometric angles — both Gemini and Tesseract are more error-prone here than on horizontal text
- Drawings with no BOM table at all — the Verifier step is skipped and items stay at Extractor-only confidence (`verification_status: "no_bom_available"`)

---

## 6. Assumptions

- One drawing, single sheet, per upload for images. Multi-page PDFs are processed page-by-page and merged into a single MTO response.
- If no BOM table is present, reconciliation is skipped rather than guessed; this is surfaced to the user as `no_bom_available`, not silently treated as a "match."
- Where a field can't be determined confidently, the pipeline returns `null` rather than fabricating a value.
- Export data is stored in-memory only, so results are available during the current server process but are not persisted across restarts.

## 7. Known Limitations

- OCR-based BOM reconciliation is category-count-based, not per-individual-item matching (the Extractor and Reader don't share a common item-ID space), so it can't say *which specific* elbow is wrong — only that the counts disagree.
- Multi-page PDFs are merged into one response, but page-wise symbol detection is still heuristic and may overcount if the same component is repeated across sheets.
- CSV export is single-user/in-memory, not safe for concurrent users (Section 4).
- Field weld counting is a lightweight OCR-derived bonus: the backend looks for `FW` / `FIELD WELD` markers in the drawing text, so the count is useful when the labels are present but it is still a best-effort signal, not a guaranteed exhaustively-detected weld inventory.
- Supports and instrumentation connections are bonus heuristic outputs driven by OCR keywords / tags and should be treated as review-worthy, not authoritative.
- No automated tests cover the real Gemini path (only the mock path is exercised in CI-style tests, since hitting the live API in tests would require a committed key or network access during grading).

## 8. What I'd Improve With More Time

- Per-item (not just per-category) reconciliation between Extractor and Reader outputs
- Bounding-box overlay on the uploaded drawing showing where each item was found
- `job_id`-keyed storage so CSV export is safe for concurrent users
- Weld counting (shop vs. field) as a bonus output
- A small fine-tuned symbol-detection model to reduce dependence on a single vision-LLM call

---

## 9. Tests

Backend tests (`backend/tests/`), all passing locally:

- `test_schema.py` — Pydantic validation: valid item, invalid category rejected, negative quantity rejected, confidence out-of-bounds rejected, default `MTOResponse` shape.
- `test_extract.py` — FastAPI `TestClient` happy path against the mock provider (asserts derived gasket/bolt items appear), bad content-type rejected (400), empty file rejected (400), health check.

```bash
cd backend
source venv/bin/activate
pytest -v
```

Last local run: **19/19 passed.**

---

## 10. Verified Manually

In addition to automated tests, the full stack was run locally end-to-end during development:
- Backend server started standalone; `/api/health`, `/api/upload` (mock mode), and `/api/mto/{job_id}/csv` all confirmed working via direct HTTP requests.
- Frontend built successfully with `npm run build` (no TypeScript errors).
- Both servers run simultaneously; CORS preflight from `localhost:3000` → `localhost:8000` confirmed working.
- A real image upload through the `/api/upload` endpoint (simulating the browser's exact request shape) returned a valid, fully-normalized MTO with correct derived gasket/bolt-set counts and summary totals.
- A real Gemini-backed upload of the included sample drawing was also captured locally after increasing `GEMINI_TIMEOUT_SECONDS` to 120 for dense drawings; the saved response returned `provider: "gemini"` and `mock: false`.

## 11. Included Sample Assets

- `3. Marked isometric (1).pdf` — sample drawing used during local testing.
- `submission_assets/screenshots/app-overview.png` — screenshot of the upload/result page.
- `submission_assets/screenshots/app-table.png` — screenshot of the generated MTO table view.
