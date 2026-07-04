# How figgydeck works

This document explains the extraction pipeline in detail, for anyone trying
to debug a misbehaving extraction or extend support to a new publisher's
template.

## The matching problem

The hard part of extracting figures from a textbook PDF is: **PDF stream
order is not figure order.** When `pdfimages` extracts every embedded bitmap,
the resulting files are in the order they appear in the byte stream, which
is determined by the typesetter's source-document layout — not by the figure
numbers a reader sees on the page.

For example, on a page with two figures (1.16 in the left column, 1.17 in
the right column), the typesetter may have inserted the right-column image
first. `pdfimages` then writes:
    - `img-015.png` ← actually shows Fig 1.17 (the right column)
    - `img-016.png` ← actually shows Fig 1.16 (the left column)

A naive "Nth image is figure N" mapping gets these backwards. In a typical
chapter this can affect a meaningful fraction of the figures.

## The matching solution

Figure labels (the visible "FIGURE 1.17" text) are reliably distinguishable
from body text by **font size**: in Elsevier-style layouts,
labels are 9 pt, captions are 8 pt, and body text is 10 pt.

`pdfplumber` exposes per-character font metadata, so we can:

1. Find every "FIGURE X.Y" or "TABLE X.Y" label by filtering for 9 pt chars
   and parsing the resulting line text with a regex.
2. For each label, find the embedded image whose **bottom edge** is just
   above the label's y-coordinate, in the **same column** as the label.
3. That image is the figure the label describes.

This is robust to stream-order shuffling because we're working in
post-rendering visual space, not pre-rendering source-document space.

## Caption extraction

Caption body text is the next signal: 8 pt, in the same column as the label,
between the label's y-coordinate and the next layout boundary (next label,
next image, or page bottom).

Filtering page chars by `abs(c["size"] - 8.0) < 0.3` and reconstructing the
text from char positions (with newlines on big y-jumps and spaces on x-gaps
> 1.5 pt) gives clean caption text — almost always exactly what was printed
in the book.

A small amount of cruft can leak in:
- Running headers (an all-caps chapter/book banner) that happen to land
  at 8 pt and overlap the column being captured.
- Footnote text that appears at the same ~8 pt size as captions.

`figgydeck.clean.clean_caption` strips these by pattern-match.

## Table extraction

Tables don't have embedded images in the PDF — they're drawn with vector
text and horizontal rule lines. So the strategy is:

1. Identify TABLE labels (same font-size approach as figures).
2. Find horizontal rules (`page.edges` filtered for orientation="h", width
   > 60pt, excluding page-margin decorations) that bracket the table.
3. Compute a bounding box from the label's position to the bottom rule.
4. Rasterize that single page with `pdftoppm` at 200 DPI and crop the
   bounding box with PIL.
5. Save as a PNG and reference it in the manifest like any other figure.

## Pipeline summary

```
chapter.pdf
   │
   ├─► pdfimages -png  ─► images/img-NNN.png  (every embedded bitmap)
   │
   ├─► pdfplumber walks pages
   │       ├─► find FIGURE/TABLE labels (9pt chars + regex)
   │       ├─► find caption text (8pt chars in same column)
   │       ├─► find table bounding boxes (horizontal rules)
   │       └─► match labels to images (geometric, column-aware)
   │
   ├─► pdftoppm + PIL crop tables  ─► images/table-X_Y.png
   │      (only when --tables / include_tables=True; skipped by default
   │       since 0.2.0 — figures-only is the common case)
   │
   ├─► clean_caption()  (ligatures, headers, hyphenation)
   │
   └─► manifest.json   ◄── single source of truth for downstream builders

manifest.json + images/
   │
   ├─► genanki  ─► .apkg
   │
   └─► python-pptx  ─► .pptx (optional)
```

## Adapting to other publishers

The font-size constants in `layout.py` are tuned to Elsevier-style layouts:

```python
LABEL_SIZE = 9.0      # "FIGURE X.Y" / "TABLE X.Y"
CAPTION_SIZE = 8.0    # caption body text
SIZE_TOL = 0.3        # how close to the target a font size must be (pt)
```

For other publishers, run `pdfplumber`'s font inspection on a representative
page and update these. The label regex (`LABEL_RE` in `layout.py`) may also
need adjusting — some publishers use "Fig." instead of "FIGURE", capitalized
differently, or use bold/italic instead of a font-size differential.

## What's NOT done by figgydeck

- **OCR.** All extraction is from the PDF's text layer. Scanned PDFs
  without OCR'd text won't work. Run `ocrmypdf` first.
- **Section detection.** The chapter's section structure (II, III, IV...)
  could be inferred from same heuristics, but figgydeck doesn't do this
  yet. Sections are passed in via the `--chapter` CLI flag for now.
- **Title generation.** Figures in this template don't have explicit titles,
  just running prose captions. If you want titles for the Anki card front,
  you'd need a separate enrichment step (an LLM does this well).
