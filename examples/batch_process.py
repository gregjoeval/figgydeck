"""Example: drive figgydeck programmatically (instead of via the CLI).

Useful when you want to:
    - process a directory of chapters in one go
    - merge per-chapter manifests into one book-level deck
    - apply custom post-processing to captions before building the deck
"""

from pathlib import Path

from figgydeck import build_apkg, extract_chapter

CHAPTERS_DIR = Path("./pdfs")  # one PDF per chapter
OUTPUT_DIR = Path("./out")
BOOK_TITLE = "The Laboratory Rat (3rd ed., 2020)"

OUTPUT_DIR.mkdir(exist_ok=True)

for pdf_path in sorted(CHAPTERS_DIR.glob("ch*.pdf")):
    chapter_num = pdf_path.stem  # e.g. "ch01"
    chapter_title = f"Chapter {int(chapter_num[2:])}"

    # 1. Extract figures, tables, captions
    extracted_dir = OUTPUT_DIR / chapter_num
    manifest = extract_chapter(pdf_path, extracted_dir, include_tables=True)

    # 2. Build .apkg
    apkg_path = OUTPUT_DIR / f"{pdf_path.stem}.apkg"
    build_apkg(
        manifest,
        extracted_dir / "images",
        BOOK_TITLE,
        chapter_title,
        apkg_path,
    )

    print(f"  ✓ {pdf_path.name} → {apkg_path.name}")

print("\nDone. Import the .apkg files into Anki via File → Import.")
