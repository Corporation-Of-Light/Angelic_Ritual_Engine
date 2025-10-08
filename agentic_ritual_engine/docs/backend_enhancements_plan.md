# Backend Enhancements Plan

## Objectives

1. Support richer metadata for symbols and rites (OCR ingestion, cross-references).
2. Improve API performance and stability for front-end integrations (Unreal, Streamlit).
3. Introduce background jobs for heavy processing (OCR, image cleanup).

## Roadmap

### Phase 1 – Data Model Extensions
- Add fields for `origin_language`, `keywords`, `confidence_score` to `Symbol`.
- Store OCR extracts per page in new table `text_fragments` linked to `TextSource`.
- Alembic migration with seed scripts (requires poppler/Tesseract path configuration).

### Phase 2 – API Improvements
- Pagination + sorting on `/symbols` endpoint.
- Dedicated `/symbols/{slug}/images` endpoint for streaming large assets.
- Caching layer (Redis or SQLite materialized views) for popular queries.
- Rate limiting / API keys for external clients.

### Phase 3 – Processing Pipeline
- Celery or RQ worker to handle `pdf-to-images`, `detect-sigils`, `ocr_enrich` asynchronously.
- Job status endpoint `/tasks/{id}` exposing progress.
- Notification hooks (webhook/email) on job completion.

### Phase 4 – Monitoring & Observability
- Structured logging (JSON) with request IDs.
- Metrics export via Prometheus (latency, job durations).
- Error tracking (Sentry/Log aggregation).

## Dependencies
- Tesseract + PyMuPDF availability on processing nodes.
- Storage for OCR text (consider compression / chunking for large works).
- Asset pipeline alignment with front-end (naming conventions, CDN).

## Next Actions
- Draft Alembic migration skeleton for new fields.
- Benchmark current `/symbols` query under sample load.
- Evaluate lightweight job queue (e.g., dramatiq) for integration.
- Define monitoring stack (fastapi instrumentation).
