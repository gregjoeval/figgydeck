"""Build one combined .pptx slide deck from a directory of chapter PDFs.

Textbooks ship their chapters with slightly different file-naming layouts, so
this runner lets you point it at a source directory and pick how filenames are
parsed into ordered chapter titles.

Filename structures handled (``--style``):
  * single -- "Chapter-N---Title_YYYY_Book.pdf"      -> "Chapter N: Title"
  * part   -- "Chapter-P-C-Title_YYYY_Book.pdf"       -> "Chapter P.C: Title"

Use ``--recursive`` when chapters live under nested subdirectories (e.g. parts).

The chapters are extracted into out/<slug>/ and merged with --combine into a
single out/<slug>/<Book>_Combined.pptx.

Usage:
  scripts/build_combined_slides.py --src PATH --book "Book Title (1st ed., 2020)"
  scripts/build_combined_slides.py --src PATH --book "..." --style part
  scripts/build_combined_slides.py --src PATH --book "..." --recursive
  scripts/build_combined_slides.py --src PATH --book "..." --dry  # list only
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from figgydeck.cli import main as cli_main


def _slug(s: str) -> str:
    """Filesystem-safe slug for the output subdirectory name."""
    return re.sub(r"\s+", "", re.sub(r"[^\w\s]", "", s).title())


def _strip_meta_suffix(stem: str) -> str:
    """Drop the trailing '_YYYY_BookName...' publisher metadata from a stem."""
    return re.sub(r"_20\d\d_.*$", "", stem)


def _clean(rest: str) -> str:
    """Turn a dash/underscore chapter-title fragment into spaced words."""
    return re.sub(r"[-_\s]+", " ", rest).strip(" -_.")


def _parse_single(stem: str) -> tuple[tuple, str]:
    """'Chapter-10---Housing-and-Environment' -> ((10,), 'Chapter 10: Housing and Environment')."""
    stem = _strip_meta_suffix(stem)
    m = re.match(r"\s*ch(?:apter)?[\s._-]*0*(\d+)[\s._-]+(.*)$", stem, re.IGNORECASE)
    if not m:
        return (9999,), _clean(stem) or stem
    num = int(m.group(1))
    rest = _clean(m.group(2))
    return (num,), (f"Chapter {num}: {rest}" if rest else f"Chapter {num}")


def _parse_part(stem: str) -> tuple[tuple, str]:
    """'Chapter-2-10-Studying-Immunology' -> ((2,10), 'Chapter 2.10: Studying Immunology')."""
    stem = _strip_meta_suffix(stem)
    m = re.match(
        r"\s*ch(?:apter)?[\s._-]*0*(\d+)[\s._-]+0*(\d+)[\s._-]+(.*)$", stem, re.IGNORECASE
    )
    if not m:
        return (9999, 9999), _clean(stem) or stem
    part, chap = int(m.group(1)), int(m.group(2))
    rest = _clean(m.group(3))
    label = f"Chapter {part}.{chap}"
    return (part, chap), (f"{label}: {rest}" if rest else label)


def gather(src: Path, style: str, recursive: bool) -> list[tuple[Path, str]]:
    """Return [(pdf, title), ...] in reading order for the source directory."""
    pdfs = src.rglob("*.pdf") if recursive else src.glob("*.pdf")
    parse = _parse_part if style == "part" else _parse_single
    parsed = [(parse(p.stem), p) for p in pdfs]
    # Order by the full numeric key ((num,) or (part, chap)), then filename for ties.
    parsed.sort(key=lambda t: (t[0], t[1].name))
    return [(p, title) for (_key, title), p in parsed]


def build(src: Path, book: str, style: str, recursive: bool, out_root: Path, dry: bool) -> int:
    chapters = gather(src, style, recursive)
    out_dir = out_root / _slug(book)
    print(f"\n=== {book} — {len(chapters)} chapters -> {out_dir}/ ===", flush=True)
    for _pdf, title in chapters:
        print(f"    {title}")
    if not chapters:
        print(f"no PDFs found under {src}", file=sys.stderr)
        return 1
    if dry:
        return 0

    # CLI expects positional PDFs first, then one --chapter per PDF in order.
    argv: list[str] = [str(pdf) for pdf, _ in chapters]
    for _, title in chapters:
        argv += ["--chapter", title]
    argv += ["--book", book, "--combine", "--format", "pptx", "--output", str(out_dir)]
    return cli_main(argv)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--src", required=True, type=Path, help="Directory containing the chapter PDFs")
    p.add_argument("--book", required=True, help="Book title, e.g. 'Book Title (1st ed., 2020)'")
    p.add_argument(
        "--style", choices=("single", "part"), default="single",
        help="Filename numbering: 'single' (Chapter N) or 'part' (Chapter P.C). Default: single.",
    )
    p.add_argument("--recursive", action="store_true", help="Recurse into subdirectories for PDFs")
    p.add_argument("--output", type=Path, default=Path("out"), help="Output root directory (default: out)")
    p.add_argument("--dry", action="store_true", help="List order + titles, extract nothing")
    args = p.parse_args(argv)
    return build(args.src, args.book, args.style, args.recursive, args.output, args.dry)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
