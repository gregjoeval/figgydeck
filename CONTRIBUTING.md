# Contributing to figgydeck

## Quick development setup

```bash
git clone https://github.com/YOUR_USERNAME/figgydeck.git
cd figgydeck
python -m venv .venv
source .venv/bin/activate    # or `.venv\Scripts\activate` on Windows
pip install -e ".[dev,pptx]"

# Run tests
pytest

# Lint
ruff check src tests
```

## Repo layout

```
figgydeck/
├── src/figgydeck/         ← the package
│   ├── extract.py         high-level pipeline
│   ├── layout.py          font/geometry-based label & caption detection
│   ├── images.py          pdfimages wrapping + table cropping
│   ├── clean.py           caption text post-processing
│   ├── anki.py            .apkg builder
│   ├── pptx.py            .pptx builder (optional dependency)
│   └── cli.py             argparse entry point
├── tests/                 unit + smoke tests
├── examples/              illustrative scripts
└── docs/HOW_IT_WORKS.md   pipeline architecture
```

## Adding support for a new publisher's layout

The font-size constants in `src/figgydeck/layout.py` are the main tunables.
Test on a representative chapter:

```python
import pdfplumber
with pdfplumber.open("chapter.pdf") as pdf:
    page = pdf.pages[3]
    fonts = {}
    for c in page.chars:
        key = (c["fontname"], round(c["size"], 1))
        fonts.setdefault(key, []).append(c["text"])
    for (name, size), sample in sorted(fonts.items(), key=lambda x: -len(x[1])):
        preview = "".join(sample[:60])
        print(f"  {name} {size}pt — {len(sample)} chars — {preview!r}")
```

Look for the font sizes used by:
- The "FIGURE X.Y" label (typically bold, smaller than body)
- The caption body text (typically slightly smaller than body)
- The body text itself (the most common size)

If the publisher uses a layout substantially different from Elsevier
(e.g. captions to the right of figures rather than below), the geometric
matcher in `layout.py` will need adjustment too. Open an issue with a
sample PDF and we'll figure it out together.

## Testing with copyrighted PDFs

The smoke test in `tests/test_chapter1.py` requires a chapter PDF from
*The Laboratory Rat* (3rd ed.) at `tests/fixtures/laboratory_rat_ch1.pdf`.
This file is not committed — it's copyrighted. The test gracefully skips
if the file isn't present. Place your own copy there to run the smoke test
locally.

## Pull requests

- Keep changes focused. One concern per PR.
- Add a unit test if you fix a bug.
- Update `docs/HOW_IT_WORKS.md` if you change the extraction pipeline.
- Run `ruff check src tests` and `pytest` before pushing.
