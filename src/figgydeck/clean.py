"""Caption cleanup: strip running headers, decode ligatures, normalize whitespace."""

from __future__ import annotations

import re

# Common PDF font ligatures
LIGATURES = {
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
    "ﬅ": "ft", "ﬆ": "st",
}

# A running header/footer is a banner of consecutive ALL-CAPS words (the book or
# chapter title) that PDF extraction interleaves into the caption text. We treat
# any run of >= 3 consecutive capitalized tokens -- with short lowercase
# connectors like "of"/"the" allowed between them -- as such a banner and strip
# it. This is a heuristic: ordinary captions rarely contain three consecutive
# all-caps words with no intervening punctuation (acronym lists like "DNA, RNA"
# are punctuated, so they don't match and are preserved).
_CAPS_WORD = r"[A-Z][A-Z0-9&.'\-]*"
_CONNECTOR = r"(?:of|the|and|in|for|to|a|an|&)"
RUNNING_HEADER_RE = re.compile(
    rf"{_CAPS_WORD}(?:(?:\s+{_CONNECTOR})*\s+{_CAPS_WORD}){{2,}}"
)

# Per-line footnote patterns are publisher-specific; none are enabled by default.
# Add re.compile(...) entries here to drop footnote lines for a particular layout.
FOOTNOTE_LINE_PATTERNS: list[re.Pattern[str]] = []


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
    text = RUNNING_HEADER_RE.sub(" ", text)

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

    # 7. Second running-header pass: catches banners that only became adjacent
    #    once line breaks were collapsed (header bled onto the caption tail).
    text = RUNNING_HEADER_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def split_camel(s: str) -> str:
    """Restore spaces in CamelCase strings extracted from PDF.

    pdfplumber sometimes concatenates chars without inferring spaces, giving
    us "RatStrainsandStocksOriginated...". This restores it to readable form.
    """
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
