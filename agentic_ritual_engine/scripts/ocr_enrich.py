"""OCR and metadata enrichment utility for ritual sources."""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Iterable

import pytesseract
from PIL import Image

try:  # optional dependency
    from pdf2image import convert_from_path

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    convert_from_path = None  # type: ignore
    PDF2IMAGE_AVAILABLE = False

try:  # optional fallback renderer
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:  # pragma: no cover - optional
    fitz = None  # type: ignore
    PYMUPDF_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="[ocr] %(message)s")
LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract text metadata from ritual PDFs.")
    parser.add_argument("pdf", type=Path, help="Path to the PDF asset.")
    parser.add_argument(
        "--pages",
        type=str,
        default="1-5",
        help="Page range to sample, e.g., '1-3,10'. Default: 1-5",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Rendering DPI for pdf2image conversion (default 300).",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="eng",
        help="Tesseract language code (requires traineddata installed).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ocr_metadata.json"),
        help="Output JSON file summarising metadata findings.",
    )
    return parser.parse_args()


def parse_page_ranges(expression: str) -> Iterable[int]:
    for part in expression.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            yield from range(int(start), int(end) + 1)
        else:
            yield int(part)


def ocr_pdf(pdf_path: Path, pages: Iterable[int], dpi: int, language: str) -> list[dict[str, Any]]:
    images = []
    min_page = min(pages)
    max_page = max(pages)
    if PDF2IMAGE_AVAILABLE and convert_from_path:
        try:
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=min_page,
                last_page=max_page,
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            LOGGER.warning("pdf2image failed (%s). Falling back to PyMuPDF if available.", exc)
            images = []

    if not images:
        if not PYMUPDF_AVAILABLE:
            raise RuntimeError(
                "Unable to render PDF. Install poppler for pdf2image or PyMuPDF for fallback."
            )
        if fitz is None:
            raise RuntimeError("PyMuPDF import failed unexpectedly.")

        doc = fitz.open(pdf_path)
        try:
            for page_number in range(min_page, max_page + 1):
                if page_number not in pages:
                    continue
                page = doc.load_page(page_number - 1)
                pixmap = page.get_pixmap(dpi=dpi)
                mode = "RGBA" if pixmap.alpha else "RGB"
                image = Image.frombytes(mode, [pixmap.width, pixmap.height], pixmap.samples)
                images.append(image)
        finally:
            doc.close()

    results: list[dict[str, Any]] = []
    for offset, image in enumerate(images):
        page_number = list(sorted(pages))[offset]
        text = pytesseract.image_to_string(image, lang=language)
        results.append({"page": page_number, "text": text})
    return results


def extract_metadata(text: str) -> dict[str, Any]:
    metadata = {}
    title_match = re.search(r"Title[:\s]+(.+)", text, re.IGNORECASE)
    author_match = re.search(r"Author[:\s]+(.+)", text, re.IGNORECASE)
    year_match = re.search(r"(16|17|18|19|20)\d{2}", text)

    if title_match:
        metadata["title_guess"] = title_match.group(1).strip()
    if author_match:
        metadata["author_guess"] = author_match.group(1).strip()
    if year_match:
        metadata["year_guess"] = year_match.group(0)

    keywords = []
    for key in ("planet", "seal", "angel", "spirit", "sigil"):
        if re.search(rf"\b{key}\b", text, re.IGNORECASE):
            keywords.append(key)
    if keywords:
        metadata["keywords"] = keywords

    return metadata


def main() -> None:
    args = parse_args()
    pdf_path: Path = args.pdf.expanduser()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    page_indices = sorted(set(parse_page_ranges(args.pages)))
    LOGGER.info("Rendering %s pages at %sdpi", len(page_indices), args.dpi)

    try:
        ocr_results = ocr_pdf(pdf_path, page_indices, args.dpi, args.language)
    except pytesseract.TesseractNotFoundError as error:
        LOGGER.error("Tesseract engine not found. Install it and ensure it's on PATH.")
        raise error

    summaries = []
    for record in ocr_results:
        metadata = extract_metadata(record["text"])
        summaries.append({"page": record["page"], "metadata": metadata, "text_preview": record["text"][:200]})

    payload = {
        "pdf": str(pdf_path),
        "pages": page_indices,
        "language": args.language,
        "results": summaries,
    }

    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    LOGGER.info("Wrote metadata summary to %s", args.output)


if __name__ == "__main__":
    main()
