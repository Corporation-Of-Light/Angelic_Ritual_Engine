"""Import pipeline CLI for acquiring ritual sources and extracting sigils."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import cv2
import requests
import typer
import yaml
from pdf2image import convert_from_path
from slugify import slugify
from tqdm import tqdm
from sqlalchemy import select

from .symbolic_kb import SymbolicKnowledgeBase, TextSource, upsert_source, upsert_symbol

cli = typer.Typer(help="Acquire sources, render scans, and detect candidate sigils.")


class ImportPipeline:
    """Encapsulates ingestion and detection helpers."""

    def __init__(self, data_dir: Path | None = None, engine_url: str | None = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.data_dir = data_dir or base_dir / "data"
        self.raw_dir = self.data_dir / "raw"
        self.raw_scans_dir = self.data_dir / "raw_scans"
        self.extracted_dir = self.data_dir / "extracted"
        for directory in (self.raw_dir, self.raw_scans_dir, self.extracted_dir):
            directory.mkdir(parents=True, exist_ok=True)

        self.kb = SymbolicKnowledgeBase(engine_url=engine_url or "sqlite:///data/ritual.db")

    # ------------------------------------------------------------------
    # Source ingestion

    def ingest_sources(self, manifest_path: Path) -> list[TextSource]:
        """Ingest sources defined in a YAML manifest and persist them."""

        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = yaml.safe_load(handle) or {}

        entries = self._flatten_manifest(manifest)
        ingested: list[TextSource] = []

        for entry in entries:
            entry = dict(entry)
            title = entry.get("title") or self._derive_title(entry)
            url = entry.get("url")
            local_path = entry.get("local_path")

            if url:
                local_path = str(self._download_remote(url, title))
                typer.echo(f"[info] downloaded {url} -> {local_path}")
            elif local_path:
                resolved = Path(local_path).expanduser()
                if not resolved.exists():
                    raise FileNotFoundError(f"Local source not found: {resolved}")
                local_path = str(resolved)
            else:
                raise ValueError(f"Entry for '{title}' is missing url or local_path")

            payload = {
                "title": title,
                "author": entry.get("author"),
                "year": entry.get("year"),
                "tradition": entry.get("tradition"),
                "url": url,
                "local_path": local_path,
                "license": entry.get("license"),
                "notes": entry.get("notes"),
            }

            source = upsert_source(**payload)
            ingested.append(source)
            typer.echo(f"[info] upserted source {source.id}: {source.title}")

        return ingested

    # ------------------------------------------------------------------
    # PDF rendering

    def pdf_to_images(self, source_identifier: str, dpi: int = 300) -> list[Path]:
        """Render PDF pages into PNG images for the provided source."""

        source = self._resolve_source(source_identifier)
        if source and source.local_path:
            pdf_path = Path(source.local_path).expanduser()
            slug = self._slug_for_source(source)
        else:
            pdf_path = Path(source_identifier).expanduser()
            slug = slugify(pdf_path.stem)
            source = None

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        output_dir = self.raw_scans_dir / slug
        output_dir.mkdir(parents=True, exist_ok=True)

        typer.echo(f"[info] rendering {pdf_path} -> {output_dir}")
        pages = convert_from_path(pdf_path, dpi=dpi)
        saved_paths: list[Path] = []
        for index, image in enumerate(tqdm(pages, desc="pages"), start=1):
            page_path = output_dir / f"page{index:04}.png"
            image.save(page_path)
            saved_paths.append(page_path)

        if source:
            typer.echo(f"[info] rendered {len(saved_paths)} pages for source {source.id}")
        else:
            typer.echo(f"[warn] rendered {len(saved_paths)} pages for unmanaged source")

        return saved_paths

    # ------------------------------------------------------------------
    # Sigil detection

    def detect_sigils(
        self,
        source_identifier: str,
        min_area: int = 800,
        max_area: float = 0.25,
    ) -> list[dict[str, Any]]:
        """Detect sigil-like contours on rendered page images."""

        source = self._resolve_source(source_identifier)
        if not source:
            raise ValueError("Sigil detection requires a known TextSource (id or slug)")

        slug = self._slug_for_source(source)
        scan_dir = self.raw_scans_dir / slug
        if not scan_dir.exists():
            raise FileNotFoundError(
                f"Rendered pages not found for source '{slug}'. Run pdf-to-images first."
            )

        page_paths = sorted(scan_dir.glob("*.png"))
        if not page_paths:
            raise FileNotFoundError(f"No page images present in {scan_dir}")

        candidate_dir = self.extracted_dir / slug
        candidate_dir.mkdir(parents=True, exist_ok=True)

        candidates: list[dict[str, Any]] = []
        typer.echo(f"[info] scanning {len(page_paths)} pages for candidate sigils")

        for page_index, page_path in enumerate(page_paths, start=1):
            image = cv2.imread(str(page_path))
            if image is None:
                typer.echo(f"[warn] unable to read {page_path}")
                continue
            height, width = image.shape[:2]
            page_area = float(width * height)

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            smoothed = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
            thresh = cv2.adaptiveThreshold(
                smoothed,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                41,
                5,
            )

            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if max_area <= 1.0:
                max_area_px = max_area * page_area
            else:
                max_area_px = max_area

            for contour_index, contour in enumerate(contours, start=1):
                area = cv2.contourArea(contour)
                if area < min_area or area > max_area_px:
                    continue

                perimeter = cv2.arcLength(contour, True)
                if perimeter <= 0:
                    continue

                compactness = (perimeter ** 2) / (area + 1e-6)
                if compactness < 25:
                    continue

                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / max(h, 1)
                if aspect_ratio > 6 or aspect_ratio < 1 / 6:
                    continue

                crop_margin = max(int(min(w, h) * 0.05), 4)
                x0 = max(x - crop_margin, 0)
                y0 = max(y - crop_margin, 0)
                x1 = min(x + w + crop_margin, width)
                y1 = min(y + h + crop_margin, height)

                crop = image[y0:y1, x0:x1]
                candidate_path = candidate_dir / f"{page_path.stem}_{contour_index:02}.png"
                cv2.imwrite(str(candidate_path), crop)

                bbox = {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)}
                candidate = {
                    "source_id": source.id,
                    "source_slug": slug,
                    "page": page_index,
                    "contour": contour_index,
                    "bbox": bbox,
                    "area": area,
                    "perimeter": perimeter,
                    "compactness": compactness,
                    "path": str(candidate_path),
                }
                candidates.append(candidate)

        if candidates:
            metadata_path = candidate_dir / "candidates.jsonl"
            with metadata_path.open("w", encoding="utf-8") as handle:
                for candidate in candidates:
                    handle.write(json.dumps(candidate) + "\n")
            typer.echo(
                f"[info] captured {len(candidates)} candidate crops -> {metadata_path}"
            )
        else:
            typer.echo("[warn] no candidates detected")

        return candidates

    # ------------------------------------------------------------------
    # Cataloging helpers

    def catalog_candidate(
        self,
        source_slug: str,
        name: str,
        tradition: str,
        function: str,
        evokes_or_invokes: str,
        deity_or_spirit: str,
        page: int,
        tags: str | None = None,
    ) -> None:
        """Persist a reviewed candidate symbol into the database."""

        source = self._resolve_source(source_slug)
        if not source:
            raise ValueError(f"Source '{source_slug}' not found")

        symbol_slug = slugify(name)
        tag_values = self._parse_tags(tags)

        symbol = upsert_symbol(
            name=name,
            slug=symbol_slug,
            tradition=tradition,
            function=function,
            evokes_or_invokes=evokes_or_invokes,
            deity_or_spirit=deity_or_spirit,
            source_id=source.id,
            page_hint=str(page),
            tags=tag_values,
        )
        typer.echo(f"[info] cataloged symbol {symbol.slug} (id={symbol.id})")

    # ------------------------------------------------------------------
    # Internal helpers

    def _flatten_manifest(self, manifest: Any) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        if isinstance(manifest, list):
            iterable: Iterable[Any] = manifest
        elif isinstance(manifest, dict):
            iterable = [item for group in manifest.values() if isinstance(group, list) for item in group]
        else:
            iterable = []

        for item in iterable:
            if isinstance(item, str):
                entries.append({"url": item})
            elif isinstance(item, dict):
                entries.append(item)
        return entries

    def _derive_title(self, entry: dict[str, Any]) -> str:
        if entry.get("title"):
            return str(entry["title"])
        if entry.get("url"):
            parsed = urlparse(entry["url"])
            stem = Path(parsed.path).stem or parsed.netloc
            return stem.replace("-", " ")
        if entry.get("local_path"):
            return Path(entry["local_path"]).stem
        return "Untitled Source"

    def _download_remote(self, url: str, title: str) -> Path:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        suffix = self._guess_suffix(url, response.headers.get("content-type"))
        filename = f"{slugify(title or url)}{suffix}"
        destination = self.raw_dir / filename
        destination.write_bytes(response.content)
        return destination

    def _guess_suffix(self, url: str, content_type: str | None) -> str:
        parsed = Path(urlparse(url).path)
        if parsed.suffix:
            return parsed.suffix
        if content_type:
            if "pdf" in content_type:
                return ".pdf"
            if "html" in content_type:
                return ".html"
        return ".bin"

    def _resolve_source(self, identifier: str) -> TextSource | None:
        identifier = str(identifier).strip()
        with self.kb.get_session() as session:
            if identifier.isdigit():
                source = session.get(TextSource, int(identifier))
                if source:
                    session.expunge(source)
                    return source

            slug_target = slugify(identifier)
            results = session.execute(select(TextSource)).scalars().all()
            for candidate in results:
                if self._slug_for_source(candidate) == slug_target:
                    session.expunge(candidate)
                    return candidate
        return None

    def _slug_for_source(self, source: TextSource) -> str:
        if source.title:
            return slugify(source.title)
        if source.local_path:
            return slugify(Path(source.local_path).stem)
        if source.url:
            parsed = urlparse(source.url)
            return slugify(Path(parsed.path).stem or parsed.netloc)
        return f"source-{source.id}"

    def _parse_tags(self, tags: str | None) -> list[str]:
        if not tags:
            return []
        parsed = json.loads(tags)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        return [str(parsed)]


@cli.command("ingest-sources")
def cli_ingest_sources(
    from_path: Path = typer.Option(
        Path("data/sources.yaml"),
        "--from",
        "from_",
        help="Path to the YAML manifest of sources.",
    ),
) -> None:
    pipeline = ImportPipeline()
    pipeline.ingest_sources(from_path)


@cli.command("pdf-to-images")
def cli_pdf_to_images(
    source: str = typer.Option(..., "--source", "-s", help="Source id/slug or PDF path."),
    dpi: int = typer.Option(300, "--dpi", help="Rendering DPI for PDF pages."),
) -> None:
    pipeline = ImportPipeline()
    pipeline.pdf_to_images(source, dpi=dpi)


@cli.command("detect-sigils")
def cli_detect_sigils(
    source: str = typer.Option(..., "--source", "-s", help="Source id or slug."),
    min_area: int = typer.Option(800, "--min-area", help="Minimum contour area in pixels."),
    max_area: float = typer.Option(
        0.25, "--max-area", help="Maximum contour area (absolute or ratio <=1)."
    ),
) -> None:
    pipeline = ImportPipeline()
    pipeline.detect_sigils(source, min_area=min_area, max_area=max_area)


@cli.command("catalog-candidate")
def cli_catalog_candidate(
    source_slug: str = typer.Option(..., "--source", help="Slug or id of the source."),
    name: str = typer.Option(..., "--name", help="Human-friendly symbol name."),
    tradition: str = typer.Option(..., "--tradition", help="Tradition or lineage."),
    function: str = typer.Option(..., "--function", help="Function, e.g., sigil or seal."),
    evokes_or_invokes: str = typer.Option(
        ..., "--evokes-or-invokes", help="Describe whether the sigil evokes or invokes."
    ),
    deity_or_spirit: str = typer.Option(..., "--deity-or-spirit", help="Linked entity."),
    page: int = typer.Option(..., "--page", help="Page number hint."),
    tags: str | None = typer.Option(None, "--tags", help="JSON list of tags."),
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


if __name__ == "__main__":
    cli()
