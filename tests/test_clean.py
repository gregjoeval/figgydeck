"""Unit tests for clean.py — no PDF fixture needed."""

from figgydeck.clean import clean_caption, split_camel


def test_decodes_ligatures():
    text = "magniﬁcent ﬂowing ﬁeld"
    assert clean_caption(text) == "magnificent flowing field"


def test_strips_running_header():
    # A run of >= 3 consecutive all-caps words is treated as a header banner.
    text = "Beautiful caption text. OVERVIEW OF THE SAMPLE CHAPTER trailing"
    out = clean_caption(text)
    assert "OVERVIEW" not in out
    assert "Beautiful caption text." in out
    assert "trailing" in out


def test_preserves_punctuated_acronyms():
    # Acronym lists are punctuated, so they must NOT be mistaken for a header.
    text = "Gel showing DNA, RNA, and PCR products."
    assert clean_caption(text) == "Gel showing DNA, RNA, and PCR products."


def test_normalizes_en_dash():
    text = "From 1968e1969"
    assert clean_caption(text) == "From 1968–1969"


def test_de_hyphenates_line_wraps():
    text = "magni-\nficent"
    assert clean_caption(text) == "magnificent"


def test_collapses_whitespace():
    text = "lots   of\n\n  whitespace"
    assert clean_caption(text) == "lots of whitespace"


def test_split_camel_basic():
    assert split_camel("CellTypesAndMarkers") == "Cell Types And Markers"


def test_split_camel_idempotent():
    assert split_camel("Already Has Spaces") == "Already Has Spaces"


def test_split_camel_empty():
    assert split_camel("") == ""
