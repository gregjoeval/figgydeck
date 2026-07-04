"""Build one combined .pptx slide deck per textbook (optimized JPEGs).

The four remaining textbooks each have a slightly different file layout, so this
runner carries a small per-book config: how to find the chapter PDFs, how to
order them, and how to derive a clean chapter title.

Structures handled:
  * flat/single   -- flat dir, "Chapter-N---Title_YYYY_Book.pdf"  (Rat, Zebrafish)
  * flat/part     -- flat dir, "Chapter-P-C-Title_YYYY_Book.pdf"  (Mouse; P.C label)
  * nested/single -- chapters under "Part N - .../"                (Rabbit; recursive)

Each book is extracted into its own out/<slug>/ tree and merged with --combine
into a single out/<slug>/<Book>_Combined.pptx.

Usage:
  scripts/build_combined_slides.py            # build every book
  scripts/build_combined_slides.py rat mouse  # build a subset (by key)
  scripts/build_combined_slides.py --dry       # list order+titles, extract nothing
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from figgydeck.cli import main as cli_main

ASSETS = Path("assets")
OUT = Path("out")

BOOKS = {
    "rat": {
        "dir": "The Laboratory Rat - 3rd ed - 2020",
        "title": "The Laboratory Rat (3rd ed., 2020)",
        "recursive": False,
        "style": "single",
    },
    "zebrafish": {
        "dir": "The Zebrafish in Biomedical Research - 2020",
        "title": "The Zebrafish in Biomedical Research (2020)",
        "recursive": False,
        "style": "single",
    },
    "mouse": {
        "dir": "The Laboratory Mouse - 2nd ed - 2012",
        "title": "The Laboratory Mouse (2nd ed., 2012)",
        "recursive": False,
        "style": "part",
    },
    "rabbit": {
        "dir": "The Laboratory Rabbit GP Hamster Other Rodents - 1st ed - 2012",
        "title": "The Laboratory Rabbit, Guinea Pig, Hamster, and Other Rodents (2012)",
        "recursive": True,
        "style": "single",
    },
}


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


def gather(book: dict) -> list[tuple[Path, str]]:
    """Return [(pdf, title), ...] in reading order for one book config."""
    src = ASSETS / book["dir"]
    pdfs = src.rglob("*.pdf") if book["recursive"] else src.glob("*.pdf")
    parse = _parse_part if book["style"] == "part" else _parse_single
    parsed = [(parse(p.stem), p) for p in pdfs]
    parsed.sort(key=lambda t: (t[0][0], t[1].name))  # sort key, then name for ties
    return [(p, title) for (_key, title), p in parsed]


def build(key: str, book: dict, dry: bool) -> int:
    chapters = gather(book)
    out_dir = OUT / key
    print(f"\n=== {book['title']} — {len(chapters)} chapters -> {out_dir}/ ===", flush=True)
    for _pdf, title in chapters:
        print(f"    {title}")
    if dry:
        return 0

    # CLI expects positional PDFs first, then one --chapter per PDF in order.
    argv: list[str] = [str(pdf) for pdf, _ in chapters]
    for _, title in chapters:
        argv += ["--chapter", title]
    argv += ["--book", book["title"], "--combine", "--out", "pptx",
             "--output", str(out_dir)]
    return cli_main(argv)


def main(argv: list[str]) -> int:
    dry = "--dry" in argv
    keys = [a for a in argv if not a.startswith("--")] or list(BOOKS)
    unknown = [k for k in keys if k not in BOOKS]
    if unknown:
        print(f"unknown book(s): {unknown}; choose from {list(BOOKS)}", file=sys.stderr)
        return 2
    rc = 0
    for key in keys:
        rc |= build(key, BOOKS[key], dry)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
