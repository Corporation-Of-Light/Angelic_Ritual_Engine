# Agentic Ritual Engine

Agentic Ritual Engine is an experimental toolkit for orchestrating symbolic imports, image cleanup, and immersive visualisation of ritual knowledge. It combines a FastAPI backend, Typer CLI, Streamlit dashboard, and image-processing utilities to ingest esoteric sources, extract sigils, clean imagery, and present the catalog in static flipbooks or interactive UI.

---
## Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

The project expects Python 3.11. If your system default differs, install 3.11 (e.g., via `pyenv`) before creating the virtualenv.

---
## Project Layout

- `core/`
  - `command_parser.py` – trigger-based command routing for higher-level automation.
  - `flipbook_builder.py` – renders cleaned glyphs into static HTML flipbooks.
  - `image_cleaner.py` – cleans extracted sigils, generates thumbnails, syncs DB records.
  - `import_pipeline.py` – CLI helpers to ingest sources, render PDFs, detect sigils.
  - `jimminy_cricket_module.py` – conscience plug-in for runtime checks and reminders.
  - `meta_agent.py` – FastAPI app factory & meta-agent bootstrapper.
  - `ritual_context.py` – celestial context calculations.
  - `symbolic_kb.py` – SQLAlchemy ORM + DAO helpers for symbols, sources, rites, glyphs.
- `frontend/pulse_map_app.py` – Streamlit dashboard for context + symbol gallery.
- `data/` – curated manifest (`sources.yaml`) and storage folders for assets.
- `main.py` – Typer entry point and FastAPI host exposing REST endpoints.

---
## Data Manifest (`data/sources.yaml`)

Sources are grouped by tradition with `highlights` bullet points for quick context:
- `solomonic_grimoires`
- `enochian_archives`
- `renaissance_occult_philosophy`
- `renaissance_theurgy`
- `folk_and_magical_practice`
- `kabbalistic_currents`

Add your own PDFs or URLs under the appropriate group before running ingestion.

---
## Database & CLI Workflow

All CLI commands are available via `python -m agentic_ritual_engine.main <command>`.

```bash
# 0) Create the SQLite database
python -m agentic_ritual_engine.main kb-init

# 1) Ingest sources from the YAML manifest
python -m agentic_ritual_engine.main ingest-sources --from data/sources.yaml

# 2) Render PDFs to page images (specify source id/slug or title)
python -m agentic_ritual_engine.main pdf-to-images --source "Key of Solomon the King (Clavicula Salomonis)" --dpi 300

# 3) Detect candidate sigils from rendered pages
python -m agentic_ritual_engine.main detect-sigils --source key-of-solomon-the-king-clavicula-salomonis --min-area 1200

# 4) Catalog reviewed candidates into the knowledge base
python -m agentic_ritual_engine.main catalog-candidate \
  --source key-of-solomon-the-king-clavicula-salomonis \
  --name "Seal of Saturn" \
  --tradition "Solomonic" \
  --function "planetary_seal" \
  --evokes-or-invokes "invoke" \
  --deity-or-spirit "Saturn" \
  --page 42 \
  --tags '["planetary","saturn"]'

# 5) Clean extracted crops into transparent PNGs and create thumbnails
python -m agentic_ritual_engine.main batch-clean \
  --in data/extracted/key-of-solomon-the-king-clavicula-salomonis \
  --out data/symbols/key-of-solomon-the-king-clavicula-salomonis

# 6) Build an HTML flipbook using current filters
python -m agentic_ritual_engine.main make-flipbook --filter '{"tradition": "Solomonic"}'

# 7) Launch the Streamlit Pulse Map dashboard
python -m agentic_ritual_engine.main run-pulse-map
```

Additional handy commands:
- `python -m agentic_ritual_engine.main parse "KRONKETA assemble"` – test trigger parsing.
- `python -m agentic_ritual_engine.main run --api-host 0.0.0.0 --api-port 8080` – host the REST API.

---
## FastAPI Endpoints

Run the API with `python -m agentic_ritual_engine.main run`. Endpoints:

- `GET /symbols?query=&filters=` – list symbols. `filters` accepts JSON (e.g., `{"tradition": "Solomonic"}`).
- `GET /symbols/{slug}` – fetch a single symbol with associated images and metadata.
- `GET /images/{id}` – retrieve glyph metadata (paths, dimensions, bbox).
- `GET /context?lat=&lon=` – compute celestial context (moon phase, sunrise/sunset, planetary hour).

Example using `curl`:
```bash
curl 'http://localhost:8000/symbols?query=saturn'
```

---
## Streamlit Pulse Map

Launch with:
```bash
streamlit run agentic_ritual_engine/frontend/pulse_map_app.py
# or via CLI wrapper:
python -m agentic_ritual_engine.main run-pulse-map
```

Features:
- Sidebar filters: text search, tradition, evokes/invokes, planet, element, deity/spirit.
- Date/time + location pickers feed `compute_context` for moon/planetary hour estimates.
- Context summary metrics (moon phase, weekday, planetary hour).
- “Hot Symbols” list (newest matches) and grid gallery of thumbnails (click for full PNG).
- “Build Flipbook” button runs the flipbook builder with current filters.

Ensure the CLI workflow has produced cleaned thumbs and database entries; otherwise the gallery will be empty.

---
## Flipbook Generation

The flipbook builder pulls symbols with transparent glyphs and writes a static HTML gallery.

```bash
python -m agentic_ritual_engine.main make-flipbook --output flipbook.html --query saturn --filter '{"tradition": "Solomonic"}'
```

Output: `flipbook.html` in project root with search bar, responsive grid, and direct links to full-resolution PNGs. Host it on any static server or open locally.

---
## Jiminy Cricket Module

Drop-in conscience layer for any script.

```python
from core.jimminy_cricket_module import create_jiminy

jiminy = create_jiminy(
    checks=[lambda: Path("data").exists()],
    reminders=["Log manual review notes.", "Respect source licenses."],
)

with jiminy.conscience("ingest-pipeline"):
    if not jiminy.run_checks():
        raise RuntimeError("Preflight checks failed")
    # perform ingestion
    jiminy.affirm("Sources ingested successfully")
```

Integrate this module into other programs by importing `JiminyCricket` or `create_jiminy`, registering checks (functions returning bool) and optional reminder messages. The context manager auto-logs timing and reminders.

Packaged version available under `packages/jiminy_cricket_tools`. Install with:

```bash
pip install -e packages/jiminy_cricket_tools
```

Then import via `from jiminy_cricket_tools import create_jiminy` in external projects.

---
## Command Parser Triggers

`core/command_parser.py` maps phrases to actions:
- `"KRONKETA"` – meta-agent boardroom stub.
- `"GAVEL"` – legal simulator placeholder.
- `"HELLFIRE RECON"` – red-team reconnaissance stub.
- `"BAYESIAN SOPHIARCH"` – forecasting placeholder.
- `"SIGIL FLIPBOOK"` – invokes flipbook builder.
- `"CHRONO_WALKER"` – timeline simulation stub.
- `"NEPHILIM VOX"` – metalcore generator stub.

Usage:
```python
from core.command_parser import CommandParser

parser = CommandParser()
result = parser.parse_and_execute("Fire up the SIGIL FLIPBOOK")
print(result)
```

`result` returns `{"trigger": "sigil flipbook", "status": "ok", "result": {...}}` with action payloads.

---
## Ritual Context Utilities

`compute_context(lat, lon, dt=None)` provides:
- ISO datetime
- Latitude/longitude
- Moon phase name
- Sunrise / sunset timestamps
- Weekday string
- Planetary hour estimate (day/night hour with ruling planet)

Example:
```python
from core.ritual_context import compute_context

context = compute_context(36.1699, -115.1398)
print(context["moon_phase"], context["planetary_hour_guess"])
```

Use the output in UI dashboards, CLI logs, or to annotate flipbooks.

---
## Development Notes

- Media output directories: `data/raw/`, `data/raw_scans/`, `data/extracted/`, `data/symbols/`, `data/thumbs/`.
- Glyph metadata stored in SQLite `data/ritual.db` by default.
- Update `requirements.txt` and `PyYAML`, `astral`, `pdf2image`, etc., before running ingestion.
- For headless environments ensure poppler (PDF renderer dependency for `pdf2image`) is installed.

---
## Extending the Engine

Ideas for future modules:
- Additional detectors for text vs sigil classification.
- Integrate neural cleanup (U-Net / diffusion-based denoise) before `image_cleaner`.
- Expand `command_parser` to trigger timeline simulations or community events.
- Replace Streamlit with immersive Unreal/Unity front-end (see `CONTRIBUTING.md` plans if added).

Contributions should follow the existing ESM + double-quote coding style, with clear docs of manual verification steps.

---
## Support

Questions or ideas? Document manual steps when cataloging new sigils, cite source licenses, and submit PRs with concise Conventional Commit messages (`feat:`, `fix:`, `chore:`). The Jiminy Cricket module is available to remind you.
  
