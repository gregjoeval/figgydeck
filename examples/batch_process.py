"""Example: drive figgydeck programmatically (instead of via the CLI).

Useful when you want to:
    - process a directory of chapters in one go
    - merge per-chapter manifests into one book-level artifact
    - apply custom post-processing to captions before building the output

This example builds both output formats (PowerPoint slides and Anki cards) from
the same extraction.

Note: the CLI now handles multiple chapters natively — pass several PDFs and add
`--combine` to merge them into one artifact per format, e.g.
    figgydeck ch01.pdf ch02.pdf --book "..." --combine --out apkg,pptx
See figgydeck.build_combined_apkg / figgydeck.pptx.build_combined_pptx for the
programmatic equivalent.
"""

from pathlib import Path

from figgydeck import build_apkg, extract_chapter
from figgydeck.pptx import build_pptx  # needs the [pptx] extra

CHAPTERS_DIR = Path("./pdfs")  # one PDF per chapter
OUTPUT_DIR = Path("./out")
BOOK_TITLE = "Example Textbook (1st ed., 2020)"

OUTPUT_DIR.mkdir(exist_ok=True)

for pdf_path in sorted(CHAPTERS_DIR.glob("ch*.pdf")):
    chapter_num = pdf_path.stem  # e.g. "ch01"
    chapter_title = f"Chapter {int(chapter_num[2:])}"

    # 1. Extract figures, tables, captions
    extracted_dir = OUTPUT_DIR / chapter_num
    manifest = extract_chapter(pdf_path, extracted_dir, include_tables=True)

    images_dir = extracted_dir / "images"

    # 2. Build PowerPoint slides
    pptx_path = OUTPUT_DIR / f"{pdf_path.stem}.pptx"
    build_pptx(manifest, images_dir, BOOK_TITLE, chapter_title, pptx_path)

    # 3. Build Anki cards
    apkg_path = OUTPUT_DIR / f"{pdf_path.stem}.apkg"
    build_apkg(manifest, images_dir, BOOK_TITLE, chapter_title, apkg_path)

    print(f"  ✓ {pdf_path.name} → {pptx_path.name}, {apkg_path.name}")

print("\nDone.")
print("  • Open the .pptx files in PowerPoint, Keynote, or Google Slides.")
print("  • Import the .apkg files into Anki via File → Import.")
