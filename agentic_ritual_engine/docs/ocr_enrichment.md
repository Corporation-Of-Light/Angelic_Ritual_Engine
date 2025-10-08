# OCR & Metadata Enrichment Guide

This guide describes how to use `scripts/ocr_enrich.py` to augment your source manifest with automatically extracted metadata.

## Prerequisites

1. **System packages**
   - Install [Tesseract OCR](https://github.com/tesseract-ocr/tesseract):
     - macOS (Homebrew): `brew install tesseract`
     - Ubuntu/Debian: `sudo apt install tesseract-ocr`
     - Windows: download installer from the Tesseract project page and add it to PATH.
   - Optional: install language packs (e.g., Latin, Hebrew) as needed.
   - If Poppler utilities are unavailable, plan to install [PyMuPDF](https://github.com/pymupdf/PyMuPDF) for rendering.
2. **Python packages**
   - Already listed in `requirements.txt`: `pytesseract`, `pdf2image`, `PyMuPDF`.
   - With Poppler present, `pdf2image` provides fastest conversion. Otherwise the script falls back to PyMuPDF automatically.

## Basic Usage

```bash
source .venv/bin/activate
python scripts/ocr_enrich.py data/raw/key-of-solomon.pdf --pages 1-4,10 --language eng --output tmp/key_solomon_ocr.json
```

- `--pages`: comma-separated ranges (`1-3,8`).
- `--language`: Tesseract language code (default `eng`). Ensure the corresponding traineddata is installed.
- `--dpi`: adjust if scans are low resolution (300–400 recommended).

## Output Structure

Sample `ocr_metadata.json` snippet:

```json
{
  "pdf": "data/raw/key-of-solomon.pdf",
  "pages": [1, 2, 3],
  "language": "eng",
  "results": [
    {
      "page": 1,
      "metadata": {
        "title_guess": "CLAVICULA SALOMONIS",
        "year_guess": "1889",
        "keywords": ["seal"]
      },
      "text_preview": "..."
    }
  ]
}
```

Use the `metadata` hints to update `data/sources.yaml` or populate symbol entries (`tradition`, `page_hint`, `tags`).

## Workflow Integration

1. Run the script after downloading a new PDF.
2. Copy relevant `metadata` insights into `catalog-candidate` commands or the manifest.
3. Attach the JSON output to manual review notes for future reference.
4. If multiple languages are present (e.g., Latin and English), run the script twice with different language codes.

## Troubleshooting

- **TesseractNotFoundError**: Ensure the binary is installed and accessible via PATH; check `pytesseract.pytesseract.tesseract_cmd` override if necessary.
- **No poppler tools**: Install PyMuPDF; the script will log that it is using the fallback renderer.
- **Poor OCR quality**: Increase DPI, clean scans with `image_cleaner` routines, or switch to nearest language pack.
- **Performance**: Large PDFs take time—limit to select pages using `--pages` during triage.

## Next Steps

- Enhance `extract_metadata` to recognise more structured cues (table parsing, additional keywords).
- Store OCR extracts in the database for search.
- Automate propagation of `metadata` into `Symbol` and `TextSource` rows.
