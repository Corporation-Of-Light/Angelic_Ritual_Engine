"""Entry point for the Agentic Ritual Engine project."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict

import typer
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.command_parser import CommandParser
from core.flipbook_builder import FlipbookBuilder
from core.image_cleaner import ImageCleaner
from core.import_pipeline import ImportPipeline
from core.meta_agent import MetaAgent
from core.ritual_context import compute_context
from core.symbolic_kb import GlyphImage, Symbol, SymbolicKnowledgeBase, TextSource, init_db

cli = typer.Typer(help="Agentic ritual engine orchestration commands.")
app = FastAPI(title="Agentic Ritual Engine", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"]
)

kb = SymbolicKnowledgeBase()
command_parser = CommandParser()


def get_session() -> Session:
    session = kb.get_session()
    try:
        yield session
    finally:
        session.close()


@app.get("/symbols")
async def api_symbols(
    query: str | None = Query(default=None),
    filters: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[Dict[str, Any]]:
    filter_dict: dict[str, Any] = {}
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid filters JSON")

    stmt = (
        select(Symbol)
        .options(selectinload(Symbol.images), selectinload(Symbol.source))
    )

    if query:
        pattern = f"%{query.lower()}%"
        stmt = stmt.where(
            (Symbol.name.ilike(pattern))
            | (Symbol.slug.ilike(pattern))
            | (Symbol.tradition.ilike(pattern))
            | (Symbol.deity_or_spirit.ilike(pattern))
        )

    for key, value in filter_dict.items():
        column = getattr(Symbol, key, None)
        if column is None:
            continue
        stmt = stmt.where(column == value)

    results = session.execute(stmt).scalars().all()
    return [serialize_symbol(symbol) for symbol in results]


@app.get("/symbols/{slug}")
async def api_symbol(slug: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    stmt = (
        select(Symbol)
        .options(selectinload(Symbol.images), selectinload(Symbol.source))
        .where(Symbol.slug == slug)
    )
    symbol = session.execute(stmt).scalar_one_or_none()
    if symbol is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return serialize_symbol(symbol)


@app.get("/images/{image_id}")
async def api_image(image_id: int, session: Session = Depends(get_session)) -> dict[str, Any]:
    image = session.get(GlyphImage, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    session.refresh(image)
    serializer = {
        "id": image.id,
        "symbol_id": image.symbol_id,
        "kind": image.kind,
        "width": image.width,
        "height": image.height,
        "raster_path": image.raster_path,
        "thumb_path": image.thumb_path,
        "transparent_bg": image.transparent_bg,
        "bbox": image.bbox,
        "hash": image.hash_sha256,
    }
    session.expunge(image)
    return serializer


@app.get("/context")
async def api_context(lat: float, lon: float) -> dict[str, Any]:
    return compute_context(lat=lat, lon=lon)


def serialize_symbol(symbol: Symbol) -> dict[str, Any]:
    images = [
        {
            "id": img.id,
            "kind": img.kind,
            "width": img.width,
            "height": img.height,
            "raster_path": img.raster_path,
            "thumb_path": img.thumb_path,
            "transparent_bg": img.transparent_bg,
            "bbox": img.bbox,
        }
        for img in (symbol.images or [])
    ]
    return {
        "id": symbol.id,
        "name": symbol.name,
        "slug": symbol.slug,
        "tradition": symbol.tradition,
        "function": symbol.function,
        "evokes_or_invokes": symbol.evokes_or_invokes,
        "deity_or_spirit": symbol.deity_or_spirit,
        "planet": symbol.planet,
        "element": symbol.element,
        "tags": symbol.tags,
        "source": symbol.source.title if symbol.source else None,
        "page_hint": symbol.page_hint,
        "images": images,
    }


@cli.command("kb-init")
def cli_kb_init(engine_url: str = typer.Option("sqlite:///data/ritual.db")) -> None:
    init_db(engine_url)
    typer.echo(f"[info] database initialised at {engine_url}")


@cli.command("ingest-sources")
def cli_ingest_sources(manifest: Path = typer.Option(Path("data/sources.yaml"), "--from")) -> None:
    pipeline = ImportPipeline()
    pipeline.ingest_sources(manifest)


@cli.command("pdf-to-images")
def cli_pdf_to_images(
    source: str = typer.Option(..., "--source"),
    dpi: int = typer.Option(300, "--dpi"),
) -> None:
    pipeline = ImportPipeline()
    pipeline.pdf_to_images(source, dpi=dpi)


@cli.command("detect-sigils")
def cli_detect_sigils(
    source: str = typer.Option(..., "--source"),
    min_area: int = typer.Option(800, "--min-area"),
    max_area: float = typer.Option(0.25, "--max-area"),
) -> None:
    pipeline = ImportPipeline()
    pipeline.detect_sigils(source, min_area=min_area, max_area=max_area)


@cli.command("catalog-candidate")
def cli_catalog_candidate(
    source_slug: str = typer.Option(..., "--source"),
    name: str = typer.Option(..., "--name"),
    tradition: str = typer.Option(..., "--tradition"),
    function: str = typer.Option(..., "--function"),
    evokes_or_invokes: str = typer.Option(..., "--evokes-or-invokes"),
    deity_or_spirit: str = typer.Option(..., "--deity-or-spirit"),
    page: int = typer.Option(..., "--page"),
    tags: str | None = typer.Option(None, "--tags"),
) -> None:
    pipeline = ImportPipeline()
    pipeline.catalog_candidate(
        source_slug=source_slug,
        name=name,
        tradition=tradition,
        function=function,
        evokes_or_invokes=evokes_or_invokes,
        deity_or_spirit=deity_or_spirit,
        page=page,
        tags=tags,
    )


@cli.command("batch-clean")
def cli_batch_clean(
    in_dir: Path = typer.Option(..., "--in"),
    out_dir: Path = typer.Option(..., "--out"),
    target_px: int = typer.Option(2000, "--target-px"),
    symbol_slug: str | None = typer.Option(None, "--symbol"),
) -> None:
    cleaner = ImageCleaner()
    cleaner.batch_clean(in_dir=in_dir, out_dir=out_dir, target_px=target_px, symbol_slug=symbol_slug)


@cli.command("make-flipbook")
def cli_make_flipbook(
    output: Path = typer.Option(Path("flipbook.html"), "--output"),
    filter_expr: str | None = typer.Option(None, "--filter"),
    query: str | None = typer.Option(None, "--query"),
) -> None:
    builder = FlipbookBuilder()
    filters = {} if not filter_expr else json.loads(filter_expr)
    count = builder.build_html_flipbook(output_path=output, query=query, filters=filters)
    typer.echo(f"[info] flipbook generated with {count} symbols -> {output}")


@cli.command("run-pulse-map")
def cli_run_pulse_map() -> None:
    script = Path(__file__).resolve().parent / "frontend" / "pulse_map_app.py"
    typer.echo(f"[info] launching Streamlit app: {script}")
    subprocess.run(["streamlit", "run", str(script)], check=True)


@cli.command("parse")
def cli_parse(text: str = typer.Argument(...)) -> None:
    result = command_parser.parse_and_execute(text)
    typer.echo(json.dumps(result, indent=2))


@cli.command("run")
def cli_run(api_host: str = "0.0.0.0", api_port: int = 8000) -> None:
    typer.echo("[info] Bootstrapping meta-agent context")
    agent = MetaAgent()
    agent.bootstrap()

    uvicorn.run(
        "main:app",
        host=api_host,
        port=api_port,
        factory=False,
        log_level="info",
    )


@cli.command("version")
def cli_version() -> None:
    typer.echo("agentic-ritual-engine 0.2.0")


if __name__ == "__main__":
    cli()
