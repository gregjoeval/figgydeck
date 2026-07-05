"""High-level extraction: chapter PDF → manifest.json + images/ folder.

This is the main entry point that orchestrates layout detection, image
extraction, table cropping, and caption cleanup.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pdfplumber

from figgydeck.clean import clean_caption, split_camel
from figgydeck.images import (
    extract_embedded_images,
    render_table_image,
    stream_index_to_filename,
)
from figgydeck.layout import extract_page
from figgydeck.models import MANIFEST_VERSION


@dataclass
class ManifestEntry:
    """One line in the chapter manifest. JSON-serializable."""
    number: str
    type: str           # "figure" | "table"
    title: str | None   # title for tables; None for figures
    caption: str        # cleaned caption text; "" for tables
    page: int
    image_filename: str | None


def extract_chapter(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    include_tables: bool = False,
    verbose: bool = True,
) -> list[dict]:
    """Extract figures (and optionally tables) and captions from a chapter PDF.

    Args:
        pdf_path: Source chapter PDF.
        output_dir: Where to write `manifest.json` and `images/` folder.
        include_tables: When True, detect and render tables and include them in
            the manifest. When False (default — changed in 0.2.0; previously
            tables were always included), tables are skipped entirely.
        verbose: Print progress.

    Returns:
        The manifest as a list of dicts (also written to `manifest.json`).
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    log = print if verbose else (lambda *a, **k: None)

    # 1. Extract every embedded image as a PNG
    log("[1/3] Extracting embedded images...")
    page_to_streams = extract_embedded_images(pdf_path, images_dir)
    total_streams = sum(len(v) for v in page_to_streams.values())

    # 2. Walk pages with pdfplumber, identify labels/captions/tables
    log("[2/3] Parsing pages for figures, tables, and captions...")
    manifest: list[ManifestEntry] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            page_num = page_idx + 1
            entries = extract_page(page, page_num)
            streams_on_page = page_to_streams.get(page_num, [])

            for entry in entries:
                if entry.type == "table" and not include_tables:
                    continue
                # Determine the image file for this entry (if any)
                if entry.type == "figure" and entry.matched_image_idx_on_page is not None:
                    if entry.matched_image_idx_on_page < len(streams_on_page):
                        sidx = streams_on_page[entry.matched_image_idx_on_page]
                        image_filename = stream_index_to_filename(sidx, total_streams)
                    else:
                        image_filename = None
                elif entry.type == "table" and entry.table_bbox:
                    image_filename = f"table-{entry.number.replace('.', '_')}.png"
                    ok = render_table_image(
                        pdf_path, entry.page,
                        entry.table_bbox, entry.page_size,
                        images_dir / image_filename,
                    )
                    if not ok:
                        image_filename = None
                else:
                    image_filename = None

                # Title and caption resolution
                if entry.type == "table":
                    raw_title = entry.inline_title or ""
                    title = split_camel(raw_title) or None
                    caption = ""  # body of table lives in the rendered image
                else:
                    title = None  # figures don't have explicit titles in this layout
                    caption = clean_caption(entry.caption_raw)

                manifest.append(ManifestEntry(
                    number=entry.number,
                    type=entry.type,
                    title=title,
                    caption=caption,
                    page=entry.page,
                    image_filename=image_filename,
                ))

    # 3. Write manifest
    log("[3/3] Writing manifest...")
    manifest_dicts = [asdict(e) for e in manifest]
    out_path = output_dir / "manifest.json"
    out_path.write_text(json.dumps(
        {"version": MANIFEST_VERSION, "entries": manifest_dicts},
        indent=2, ensure_ascii=False,
    ))

    n_fig = sum(1 for e in manifest if e.type == "figure")
    n_tab = sum(1 for e in manifest if e.type == "table")
    log(f"  wrote {out_path}")
    if include_tables:
        log(f"  found {n_fig} figures, {n_tab} tables")
    else:
        log(f"  found {n_fig} figures (tables skipped)")

    return manifest_dicts
