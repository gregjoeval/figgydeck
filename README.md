# figgydeck

[![tests](https://github.com/gregjoeval/figgydeck/actions/workflows/tests.yml/badge.svg)](https://github.com/gregjoeval/figgydeck/actions/workflows/tests.yml)

> Turn textbooks into study decks. Extract figures, tables, and their captions from chapter PDFs, then package them as PowerPoint slides or Anki flashcard decks.

`figgydeck` reads a chapter PDF and finds every figure and table along with its
caption. It gives you one slide or card per figure — the image on the face, and
the caption plus book/chapter/page metadata attached — the format you actually
want for visual recall or lecture review.

Two output formats, same extraction:

- **PowerPoint** (`.pptx`) — one slide per figure/table, image centered with its
  aspect ratio preserved and the metadata in the slide's speaker notes. Opens in
  PowerPoint, Keynote, or Google Slides.
- **Anki** (`.apkg`) — one card per figure/table, image on the front and the
  caption + metadata on the back. Imports straight into Anki.

## Why

Manually building slides or flashcards from a 40-figure chapter takes hours. The two
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
# One command, chapter PDF → figure deck (figures only by default)
figgydeck chapter1.pdf \
    --book "Example Textbook (1st ed., 2020)" \
    --chapter "Ch. 3: Cell Structure" \
    --output ./out/

# Outputs (default format is .apkg — see --out below for PowerPoint):
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

`--out` defaults to `apkg` when omitted. PowerPoint output needs the optional
`[pptx]` extra (see [Install](#install)).

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
6. Emits a `manifest.json` plus your chosen deck(s) — `.apkg` and/or `.pptx`

On a well-behaved Elsevier-format chapter this reliably matches every figure to
its caption and crops tables with their full titles.

## What you get

Both formats carry the same content — the figure or table image plus its
caption and book/chapter/page metadata — laid out for the way you'll use it.

**PowerPoint slides** (`.pptx`)

- One slide per figure/table, image centered and scaled to fit with its aspect
  ratio preserved (no cropping)
- Number, title, caption, book, chapter, and page in the slide's speaker notes
- A combined deck (`--combine`) opens with a title slide (book + chapter count)

**Anki cards** (`.apkg`)

- A clean two-side layout that's readable in both light and dark mode
- **Front:** image only, with a small `Fig X.Y` tag below
- **Back:** type label, caption, and book/chapter/page metadata
- Stable note GUIDs based on `(book, chapter, type, number)` — re-importing
  updates existing cards rather than duplicating them

## AI assistance

Built with help from [Claude Code](https://claude.com/claude-code). All code is
human-reviewed.
