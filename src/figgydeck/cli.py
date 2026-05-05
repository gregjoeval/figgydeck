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


_VALID_FORMATS = ("apkg", "pptx")


def _format_list(s: str) -> list[str]:
    """Parse a single --out value: comma-separated formats with validation."""
    parts = [p.strip().lower() for p in s.split(",") if p.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("--out value cannot be empty")
    bad = [p for p in parts if p not in _VALID_FORMATS]
    if bad:
        raise argparse.ArgumentTypeError(
            f"unknown format(s): {', '.join(bad)} "
            f"(choose from: {', '.join(_VALID_FORMATS)})"
        )
    return parts


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="figgydeck",
        description="Turn textbooks into study decks: extract figures (and "
                    "optionally tables) and captions from chapter PDFs and "
                    "package them as Anki decks or PowerPoint slides.",
    )
    p.add_argument("pdf", help="Source chapter PDF")
    p.add_argument("--book", required=True, help="Book title (e.g. 'The Laboratory Rat (3rd ed., 2020)')")
    p.add_argument("--chapter", required=True, help="Chapter title (e.g. 'Ch. 1: Historical Foundations')")
    p.add_argument("--output", "-o", default="./out", help="Output directory (default: ./out)")
    p.add_argument(
        "--out", action="append", type=_format_list, default=None,
        metavar="FMT[,FMT...]",
        help="Output format(s). Repeatable, or comma-separated. "
             f"Choices: {', '.join(_VALID_FORMATS)}. Default: apkg.",
    )
    p.add_argument("--tables", action="store_true",
                   help="Also extract tables (default: figures only).")
    p.add_argument("--quiet", "-q", action="store_true", help="Suppress progress logging")
    args = p.parse_args(argv)

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"error: {pdf_path} does not exist", file=sys.stderr)
        return 2

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    verbose = not args.quiet

    # Flatten + dedupe requested formats while preserving order.
    chunks = args.out if args.out else [["apkg"]]
    formats = list(dict.fromkeys(f for chunk in chunks for f in chunk))

    # Bind builders up front so a missing optional dep (python-pptx) fails
    # before the slow extraction step.
    build_apkg = build_pptx = None
    if "apkg" in formats:
        from figgydeck.anki import build_apkg
    if "pptx" in formats:
        from figgydeck.pptx import build_pptx

    # Step 1: extract
    from figgydeck.extract import extract_chapter
    manifest = extract_chapter(pdf_path, out_dir, include_tables=args.tables, verbose=verbose)

    images_dir = out_dir / "images"
    base = _safe_filename(args.book, args.chapter)

    # Step 2: write requested formats
    if build_apkg is not None:
        build_apkg(manifest, images_dir, args.book, args.chapter,
                   out_dir / f"{base}.apkg", verbose=verbose)
    if build_pptx is not None:
        build_pptx(manifest, images_dir, args.book, args.chapter,
                   out_dir / f"{base}.pptx", verbose=verbose)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
