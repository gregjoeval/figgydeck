"""Caption cleanup: strip running headers, decode ligatures, normalize whitespace."""

from __future__ import annotations

import re

# Common PDF font ligatures
LIGATURES = {
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
    "ﬅ": "ft", "ﬆ": "st",
}

# Patterns matching things that look like 8pt text but aren't part of the caption
RUNNING_HEADER_PATTERNS = [
    re.compile(r"BACKGROUND OF THE LABORATORY RAT", re.I),
    re.compile(r"^\d+\.\s+HISTORICAL FOUNDATIONS$", re.I),
]

FOOTNOTE_LINE_PATTERNS = [
    re.compile(r"^\d?\s*Names of"),
]

# Footnote-style trailing sentences that bleed into long captions.
# Anything from these markers to end-of-string is stripped.
FOOTNOTE_TAIL_PATTERNS = [
    re.compile(r"\s+Names of [A-Z][a-z]+['’]?s? collaborators.*$"),
    re.compile(r"\s+BACKGROUND OF.*$"),
    re.compile(r"\s+\d+\.\s*HISTORICAL FOUNDATIONS.*$", re.I),
]


def clean_caption(text: str) -> str:
    """Clean a raw extracted caption into something readable.

    Steps:
        1. Decode font ligatures
        2. Strip running headers (anywhere they appear)
        3. Filter footnote-style lines
        4. De-hyphenate line-wrapped words
        5. Normalize the en-dash glyph
        6. Collapse whitespace
        7. Strip trailing partial words from running-header bleed
    """
    if not text:
        return ""

    # 1. Ligatures
    for lig, repl in LIGATURES.items():
        text = text.replace(lig, repl)

    # 2. Running headers (mid-text occurrences)
    for pat in RUNNING_HEADER_PATTERNS:
        text = pat.sub("", text)

    # 3. Per-line footnote filtering
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    lines = [ln for ln in lines if not any(p.match(ln) for p in FOOTNOTE_LINE_PATTERNS)]
    text = " ".join(lines)

    # 4. De-hyphenate line-wrapped words
    text = re.sub(r"-\s+", "", text)

    # 5. Elsevier renders en-dash as "e": "1968e1969" -> "1968–1969"
    text = re.sub(r"(\d{4})e(\d{4})", r"\1–\2", text)

    # 6. Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # 7. Trailing-cruft strip
    text = re.sub(r"\s*BACKGROUND.*$", "", text)
    for pat in FOOTNOTE_TAIL_PATTERNS:
        text = pat.sub("", text)

    return text.strip()


def split_camel(s: str) -> str:
    """Restore spaces in CamelCase strings extracted from PDF.

    pdfplumber sometimes concatenates chars without inferring spaces, giving
    us "RatStrainsandStocksOriginated...". This restores it to readable form.
    """
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
