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

## Usage

```bash
# One command, chapter PDF → Anki deck
figgydeck chapter1.pdf \
    --book "The Laboratory Rat (3rd ed., 2020)" \
    --chapter "Ch. 1: Historical Foundations" \
    --output ./out/

# Outputs:
#   out/LaboratoryRat_3e_Ch01_HistoricalFoundations.apkg  ← import into Anki
#   out/manifest.json                                      ← inspect what was extracted
#   out/images/                                            ← extracted figures + cropped tables
```

To also produce a slide deck:

```bash
figgydeck chapter1.pdf --book "..." --chapter "..." --output ./out --pptx
```

## How it works

For an Elsevier-format chapter, `figgydeck`:

1. Extracts all embedded images via `pdfimages`
2. Walks each PDF page with `pdfplumber`, identifying:
   - **`FIGURE X.Y` / `TABLE X.Y` labels** by font size (9 pt bold)
   - **caption text** by font size (8 pt) within column-aware bounding boxes
   - **table regions** by horizontal-rule detection
3. Matches each label to the nearest image whose bottom edge sits just above it
   in the same column — robust to images appearing in shuffled stream order
4. Crops table regions from rasterized pages
5. Cleans captions (strips running headers, decodes ligatures, de-hyphenates
   line wraps)
6. Emits a `manifest.json` plus the Anki `.apkg`

Validated on chapter 1 of *The Laboratory Rat* (3rd ed.): 53/53 figures matched
correctly, 2/2 tables cropped with full titles.

## Card design

The Anki card model uses a clean two-side layout that's readable in both light
and dark mode:

- **Front:** image only, with a small `Fig X.Y` tag below
- **Back:** type label, caption, and book/chapter/page metadata
- Stable note GUIDs based on `(book, chapter, type, number)` — re-importing
  updates existing cards rather than duplicating them

## Status

Active development. Supports the Elsevier laboratory-animal textbook series.
Other publishers may need template adjustments to the font-size constants.

## License

MIT
