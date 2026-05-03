"""figgydeck command-line interface."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _safe_filename(book: str, chapter: str) -> str:
    """Build a clean filename from book + chapter titles.

    Examples:
        "The Laboratory Rat (3rd ed., 2020)", "Ch. 1: Historical Foundations"
        → "LaboratoryRat3e_Ch01_HistoricalFoundations"
    """
    def slug(s: str) -> str:
        # collapse whitespace and remove punctuation, keep alphanumerics
        s = re.sub(r"[^\w\s]", "", s)
        s = re.sub(r"\s+", "", s.title())
        return s

    return f"{slug(book)}_{slug(chapter)}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="figgydeck",
        description="Turn textbooks into study decks: extract figures, tables, "
                    "and captions from chapter PDFs and package them as Anki decks.",
    )
    p.add_argument("pdf", help="Source chapter PDF")
    p.add_argument("--book", required=True, help="Book title (e.g. 'The Laboratory Rat (3rd ed., 2020)')")
    p.add_argument("--chapter", required=True, help="Chapter title (e.g. 'Ch. 1: Historical Foundations')")
    p.add_argument("--output", "-o", default="./out", help="Output directory (default: ./out)")
    p.add_argument("--pptx", action="store_true",
                   help="Also produce a .pptx slide deck (requires figgydeck[pptx])")
    p.add_argument("--no-anki", action="store_true",
                   help="Skip the .apkg output (useful with --pptx alone)")
    p.add_argument("--quiet", "-q", action="store_true", help="Suppress progress logging")
    args = p.parse_args(argv)

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"error: {pdf_path} does not exist", file=sys.stderr)
        return 2

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    verbose = not args.quiet

    # Step 1: extract
    from figgydeck.extract import extract_chapter
    manifest = extract_chapter(pdf_path, out_dir, verbose=verbose)

    images_dir = out_dir / "images"
    base = _safe_filename(args.book, args.chapter)

    # Step 2: build .apkg (default)
    if not args.no_anki:
        from figgydeck.anki import build_apkg
        apkg_path = out_dir / f"{base}.apkg"
        build_apkg(manifest, images_dir, args.book, args.chapter, apkg_path,
                   verbose=verbose)

    # Step 3: build .pptx (optional)
    if args.pptx:
        from figgydeck.pptx import build_pptx
        pptx_path = out_dir / f"{base}.pptx"
        build_pptx(manifest, images_dir, args.book, args.chapter, pptx_path,
                   verbose=verbose)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
