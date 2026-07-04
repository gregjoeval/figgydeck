# figgydeck

[![tests](https://github.com/gregjoeval/figgydeck/actions/workflows/tests.yml/badge.svg)](https://github.com/gregjoeval/figgydeck/actions/workflows/tests.yml)

> Turn textbooks into study decks. Extract figures, tables, and their captions from chapter PDFs, then package them as Anki decks (or PowerPoint).

`figgydeck` reads a chapter PDF, finds every figure and table along with its
caption, and emits an `.apkg` file ready to import into Anki. Each card has the
figure or table on the front and the caption + book/chapter metadata on the back
— the format you actually want for visual recall.

It can also emit a `.pptx` slide deck if you want a static archive view.

## Why

Manually building flashcards from a 40-figure chapter takes hours. The two
hard parts are (1) matching extracted images to their figure numbers — PDF
stream order is often shuffled — and (2) cleaning captions of running headers
and footnotes that bleed in. `figgydeck` does both with pure-Python signal
processing (font sizes, spatial geometry, ruled-line detection); no LLM call
required for the standard Elsevier textbook layout.

## Install

```bash
pip install figgydeck
```

System requirements: `poppler` (for `pdftoppm` and `pdfimages`).

```bash
# macOS
brew install poppler

# Debian/Ubuntu
sudo apt install poppler-utils
```

PowerPoint output (`--out pptx`) needs an optional extra:

```bash
pip install "figgydeck[pptx]"
```

## Usage

```bash
# One command, chapter PDF → Anki deck (figures only by default)
figgydeck chapter1.pdf \
    --book "Example Textbook (1st ed., 2020)" \
    --chapter "Ch. 3: Cell Structure" \
    --output ./out/

# Outputs:
#   out/ExampleTextbook1StEd2020_Ch3CellStructure.apkg     ← import into Anki
#   out/manifest.json                                      ← inspect what was extracted
#   out/images/                                            ← extracted figures
```

Also include table cards (extra `pdftoppm` rasterization per table):

```bash
figgydeck chapter1.pdf --book "..." --chapter "..." --tables
```

Pick your output format(s) with `--out` (repeatable, or comma-separated):

```bash
figgydeck chapter1.pdf --book "..." --chapter "..." --out pptx           # only .pptx
figgydeck chapter1.pdf --book "..." --chapter "..." --out apkg,pptx      # both
figgydeck chapter1.pdf --book "..." --chapter "..." --out apkg --out pptx  # same
```

### Multiple chapters

Pass more than one chapter PDF in a single command. Give one `--chapter` per PDF
(in order), or omit `--chapter` entirely to derive each title from its filename
(`ch01.pdf` → "Chapter 1"):

```bash
# one artifact per chapter (like running figgydeck once per PDF)
figgydeck ch01.pdf ch02.pdf ch03.pdf --book "..." --out pptx

# --combine merges every chapter into ONE artifact per format
figgydeck ch01.pdf ch02.pdf ch03.pdf --book "..." --combine --out apkg,pptx
#   out/<Book>_Combined.pptx   ← one deck: title slide + all figures
#   out/<Book>_Combined.apkg   ← one Anki package, one subdeck per chapter
```

With multiple PDFs, each chapter is extracted into its own `out/NN_<slug>/`
subdir (so identical image names don't collide). Slide images keep their native
aspect ratio and are centered — nothing is stretched or cropped.

### Breaking changes in 0.2.0

- `--pptx` and `--no-anki` removed — use `--out apkg`, `--out pptx`, or `--out apkg,pptx`.
- Table cards are now opt-in via `--tables` (previously included by default).
- The library function `extract_chapter()` defaults `include_tables=False`. Programmatic callers that want tables must pass `include_tables=True`.

## How it works

For an Elsevier-format chapter, `figgydeck`:

1. Extracts all embedded images via `pdfimages`
2. Walks each PDF page with `pdfplumber`, identifying:
   - **`FIGURE X.Y` / `TABLE X.Y` labels** by font size (~9 pt label font)
   - **caption text** by font size (8 pt) within column-aware bounding boxes
   - **table regions** by horizontal-rule detection
3. Matches each label to the nearest image whose bottom edge sits just above it
   in the same column — robust to images appearing in shuffled stream order
4. Crops table regions from rasterized pages
5. Cleans captions (strips running headers, decodes ligatures, de-hyphenates
   line wraps)
6. Emits a `manifest.json` plus the Anki `.apkg`

On a well-behaved Elsevier-format chapter this reliably matches every figure to
its caption and crops tables with their full titles.

## Card design

The Anki card model uses a clean two-side layout that's readable in both light
and dark mode:

- **Front:** image only, with a small `Fig X.Y` tag below
- **Back:** type label, caption, and book/chapter/page metadata
- Stable note GUIDs based on `(book, chapter, type, number)` — re-importing
  updates existing cards rather than duplicating them

## Status

Active development. Tuned for Elsevier-style two-column academic layouts.
Other publishers may need template adjustments to the font-size constants.

## License

MIT
