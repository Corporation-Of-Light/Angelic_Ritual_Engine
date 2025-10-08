"""Image cleanup helpers for extracted symbols."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import typer
from PIL import Image
from slugify import slugify
from sqlalchemy import select

from .symbolic_kb import GlyphImage, Symbol, SymbolicKnowledgeBase

cli = typer.Typer(help="Clean extracted sigils and publish assets to the catalog.")


class ImageCleaner:
    """Perform thresholding, alpha masking, and catalog updates for symbol images."""

    def __init__(self, data_dir: Path | None = None, engine_url: str | None = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.data_dir = data_dir or base_dir / "data"
        self.symbols_dir = self.data_dir / "symbols"
        self.thumbs_dir = self.data_dir / "thumbs"
        self.symbols_dir.mkdir(parents=True, exist_ok=True)
        self.thumbs_dir.mkdir(parents=True, exist_ok=True)
        self.kb = SymbolicKnowledgeBase(engine_url=engine_url)

    # ------------------------------------------------------------------
    # Core cleaning logic

    def clean_to_transparent(
        self,
        in_path: Path,
        out_path: Path,
        target_px: int = 2000,
    ) -> dict[str, Any]:
        """Convert a raster sigil into a cropped, transparent PNG."""

        image = cv2.imread(str(in_path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise FileNotFoundError(f"Image not found: {in_path}")

        if image.ndim == 2:
            gray = image
            bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            if image.shape[2] == 4:
                bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            else:
                bgr = image[:, :, :3]
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        kernel_size = max(5, int(max(gray.shape) * 0.015))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        background = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        normalized = cv2.subtract(gray, background)

        _, mask = cv2.threshold(normalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        flood_seed = (0, 0)
        flood_mask = np.zeros((mask.shape[0] + 2, mask.shape[1] + 2), np.uint8)
        mask_inverted = 255 - mask
        cv2.floodFill(mask_inverted, flood_mask, flood_seed, 0)
        refined = 255 - mask_inverted

        refined = cv2.medianBlur(refined, 5)
        refined = cv2.morphologyEx(refined, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
        refined = cv2.morphologyEx(refined, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)

        alpha = refined
        rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = alpha

        height, width = rgba.shape[:2]
        longest_side = max(width, height)
        if target_px > 0 and longest_side != target_px:
            scale = target_px / float(longest_side)
            new_size = (int(round(width * scale)), int(round(height * scale)))
            if new_size[0] <= 0 or new_size[1] <= 0:
                new_size = (width, height)
            rgba = cv2.resize(
                rgba,
                new_size,
                interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
            )
            alpha = cv2.resize(alpha, new_size, interpolation=cv2.INTER_NEAREST)

        valid_pixels = np.argwhere(alpha > 0)
        if valid_pixels.size:
            y_min, x_min = valid_pixels.min(axis=0)
            y_max, x_max = valid_pixels.max(axis=0)
        else:
            x_min = y_min = 0
            y_max, x_max = rgba.shape[0] - 1, rgba.shape[1] - 1

        bbox = {
            "x": int(x_min),
            "y": int(y_min),
            "w": int(x_max - x_min + 1),
            "h": int(y_max - y_min + 1),
        }

        out_path.parent.mkdir(parents=True, exist_ok=True)
        rgba_rgba = cv2.cvtColor(rgba, cv2.COLOR_BGRA2RGBA)
        image_pil = Image.fromarray(rgba_rgba)
        image_pil.save(out_path, format="PNG")

        pixel_hash = hashlib.sha256(rgba.tobytes()).hexdigest()

        return {
            "path": out_path,
            "width": image_pil.width,
            "height": image_pil.height,
            "bbox": bbox,
            "hash": pixel_hash,
        }

    # ------------------------------------------------------------------
    # Batch helpers

    def batch_clean(
        self,
        in_dir: Path,
        out_dir: Path,
        target_px: int = 2000,
        symbol_slug: str | None = None,
    ) -> list[dict[str, Any]]:
        """Batch-clean candidate glyphs and sync database metadata."""

        in_dir = in_dir.expanduser()
        out_dir = out_dir.expanduser()
        if not in_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {in_dir}")

        files = sorted(in_dir.glob("*.png"))
        if not files:
            typer.echo(f"[warn] no PNG candidates discovered in {in_dir}")
            return []

        slug = out_dir.name or slugify(in_dir.name)
        thumbs_dir = self.thumbs_dir / slug
        thumbs_dir.mkdir(parents=True, exist_ok=True)

        cleaned: list[dict[str, Any]] = []
        for path in files:
            output_path = out_dir / path.name
            metadata = self.clean_to_transparent(path, output_path, target_px=target_px)
            thumb_path = thumbs_dir / path.name
            self._write_thumbnail(output_path, thumb_path)
            metadata["thumb_path"] = thumb_path
            metadata["source"] = path

            self._update_glyph_record(
                metadata=metadata,
                symbol_slug=symbol_slug,
            )
            cleaned.append(metadata)
            typer.echo(f"[info] cleaned {path.name} -> {output_path.name}")

        return cleaned

    # ------------------------------------------------------------------
    # Internal helpers

    def _write_thumbnail(self, image_path: Path, thumb_path: Path, size: int = 512) -> None:
        with Image.open(image_path) as image:
            image.thumbnail((size, size))
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(thumb_path, format="PNG")

    def _update_glyph_record(
        self,
        metadata: dict[str, Any],
        symbol_slug: str | None = None,
    ) -> None:
        source_file: Path = metadata.get("source")
        out_path: Path = metadata["path"]
        thumb_path: Path = metadata["thumb_path"]

        with self.kb.get_session() as session:
            glyph = None
            filename = source_file.name if source_file else out_path.name
            glyph = session.execute(
                select(GlyphImage).where(GlyphImage.raster_path.like(f"%{filename}"))
            ).scalar_one_or_none()

            if glyph is None:
                symbol = None
                if symbol_slug:
                    symbol = session.execute(
                        select(Symbol).where(Symbol.slug == symbol_slug)
                    ).scalar_one_or_none()
                    if symbol is None:
                        raise ValueError(f"Symbol with slug '{symbol_slug}' not found")
                else:
                    symbol = session.execute(
                        select(Symbol)
                        .join(GlyphImage, isouter=True)
                        .where(Symbol.slug == Path(filename).stem)
                    ).scalar_one_or_none()

                if symbol is None:
                    typer.echo(
                        f"[warn] unable to link glyph '{filename}' to a symbol; skipping DB update"
                    )
                    return

                glyph = GlyphImage(symbol_id=symbol.id, kind="cleaned")
                session.add(glyph)

            glyph.kind = glyph.kind or "cleaned"
            glyph.width = metadata["width"]
            glyph.height = metadata["height"]
            glyph.raster_path = str(out_path)
            glyph.thumb_path = str(thumb_path)
            glyph.transparent_bg = True
            glyph.bbox = metadata.get("bbox")
            glyph.hash_sha256 = metadata.get("hash")

            session.commit()


@cli.command("batch-clean")
def cli_batch_clean(
    in_dir: Path = typer.Option(..., "--in", help="Directory with extracted candidates."),
    out_dir: Path = typer.Option(..., "--out", help="Destination directory for cleaned PNGs."),
    target_px: int = typer.Option(2000, "--target-px", help="Longest dimension after scaling."),
    symbol_slug: str | None = typer.Option(
        None,
        "--symbol",
        help="Optional symbol slug to associate cleaned glyphs with.",
    ),
) -> None:
    cleaner = ImageCleaner()
    cleaner.batch_clean(
        in_dir=in_dir,
        out_dir=out_dir,
        target_px=target_px,
        symbol_slug=symbol_slug,
    )


if __name__ == "__main__":
    cli()
