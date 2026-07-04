"""figgydeck command-line interface."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _slug(s: str) -> str:
    """Collapse whitespace and strip punctuation, keeping alphanumerics.

    "Ch. 1: Historical Foundations" -> "Ch1HistoricalFoundations"
    """
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", "", s.title())
    return s


def _safe_filename(book: str, chapter: str) -> str:
    """Build a clean filename from book + chapter titles.

    Examples:
        "The Laboratory Rat (3rd ed., 2020)", "Ch. 1: Historical Foundations"
        → "LaboratoryRat3e_Ch01_HistoricalFoundations"
    """
    return f"{_slug(book)}_{_slug(chapter)}"


def _chapter_title(pdf_path: Path, explicit: str | None) -> str:
    """Resolve a chapter's display title.

    Uses `explicit` when given; otherwise derives one from the PDF filename:
    a ``ch01``-style stem becomes ``"Chapter 1"``; anything else is title-cased
    with ``-``/``_`` turned into spaces.
    """
    if explicit:
        return explicit
    stem = pdf_path.stem
    # Match a leading chapter marker and split off any descriptive remainder:
    #   "ch01"                              -> "Chapter 1"
    #   "Chapter-3-Biology-and-Diseases..." -> "Chapter 3: Biology and Diseases..."
    #   "Chapter 11 - Microbiological..."   -> "Chapter 11: Microbiological..."
    m = re.match(r"\s*ch(?:apter)?[\s._-]*0*(\d+)[\s._-]*(.*)$", stem, re.IGNORECASE)
    if m:
        num = int(m.group(1))
        rest = re.sub(r"[\s_-]+", " ", m.group(2)).strip(" _-.")
        return f"Chapter {num}: {rest}" if rest else f"Chapter {num}"
    pretty = re.sub(r"[-_]+", " ", stem).strip()
    return pretty.title() if pretty else stem


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
    p.add_argument("pdfs", nargs="+", metavar="PDF", help="One or more source chapter PDFs")
    p.add_argument("--book", required=True, help="Book title (e.g. 'The Laboratory Rat (3rd ed., 2020)')")
    p.add_argument(
        "--chapter", action="append", default=None, metavar="TITLE",
        help="Chapter title (e.g. 'Ch. 1: Historical Foundations'). Repeatable: "
             "give one per PDF, in order. If omitted, titles are derived from "
             "each PDF's filename.",
    )
    p.add_argument("--output", "-o", default="./out", help="Output directory (default: ./out)")
    p.add_argument(
        "--out", action="append", type=_format_list, default=None,
        metavar="FMT[,FMT...]",
        help="Output format(s). Repeatable, or comma-separated. "
             f"Choices: {', '.join(_VALID_FORMATS)}. Default: apkg.",
    )
    p.add_argument("--combine", action="store_true",
                   help="Merge all input PDFs into a single artifact per format.")
    p.add_argument("--full-res", action="store_true",
                   help="Embed full-resolution PNGs in .pptx (default: downscaled "
                        "JPEGs, which keep the file small enough for Google Slides).")
    p.add_argument("--tables", action="store_true",
                   help="Also extract tables (default: figures only).")
    p.add_argument("--quiet", "-q", action="store_true", help="Suppress progress logging")
    args = p.parse_args(argv)

    pdf_paths = [Path(p) for p in args.pdfs]
    missing = [p for p in pdf_paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"error: {p} does not exist", file=sys.stderr)
        return 2

    # Resolve one chapter title per PDF: all-or-nothing on --chapter.
    if args.chapter is None:
        titles = [_chapter_title(p, None) for p in pdf_paths]
    elif len(args.chapter) == len(pdf_paths):
        titles = [_chapter_title(p, c) for p, c in zip(pdf_paths, args.chapter, strict=True)]
    else:
        print(
            f"error: got {len(args.chapter)} --chapter value(s) for "
            f"{len(pdf_paths)} PDF(s); supply either none or exactly one per PDF",
            file=sys.stderr,
        )
        return 2

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    verbose = not args.quiet

    # Flatten + dedupe requested formats while preserving order.
    chunks = args.out if args.out else [["apkg"]]
    formats = list(dict.fromkeys(f for chunk in chunks for f in chunk))

    # Bind builders up front so a missing optional dep (python-pptx) fails
    # before the slow extraction step. Imported at call time so tests can
    # patch the module-level functions.
    apkg_single = apkg_combined = None
    pptx_single = pptx_combined = None
    if "apkg" in formats:
        from figgydeck.anki import build_apkg as apkg_single
        from figgydeck.anki import build_combined_apkg as apkg_combined
    if "pptx" in formats:
        from figgydeck.pptx import build_combined_pptx as pptx_combined
        from figgydeck.pptx import build_pptx as pptx_single

    # Step 1: extract each PDF. A single PDF extracts into out_dir directly
    # (preserving the classic out/images + out/manifest.json layout); multiple
    # PDFs each get their own subdir so fixed image names don't collide.
    from figgydeck.extract import extract_chapter

    single_pdf = len(pdf_paths) == 1
    chapters: list[tuple[list[dict], Path, str]] = []
    for i, (pdf, title) in enumerate(zip(pdf_paths, titles, strict=True)):
        ex_dir = out_dir if single_pdf else out_dir / f"{i:02d}_{_slug(title)}"
        manifest = extract_chapter(pdf, ex_dir, include_tables=args.tables, verbose=verbose)
        chapters.append((manifest, ex_dir / "images", title))

    # Step 2: write requested formats
    optimize = not args.full_res
    if args.combine:
        base = f"{_slug(args.book)}_Combined"
        if apkg_combined is not None:
            apkg_combined(chapters, args.book, out_dir / f"{base}.apkg", verbose=verbose)
        if pptx_combined is not None:
            pptx_combined(chapters, args.book, out_dir / f"{base}.pptx",
                          optimize_images=optimize, verbose=verbose)
    else:
        for manifest, images_dir, title in chapters:
            base = _safe_filename(args.book, title)
            if apkg_single is not None:
                apkg_single(manifest, images_dir, args.book, title,
                            out_dir / f"{base}.apkg", verbose=verbose)
            if pptx_single is not None:
                pptx_single(manifest, images_dir, args.book, title,
                            out_dir / f"{base}.pptx",
                            optimize_images=optimize, verbose=verbose)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
