"""Unit tests for clean.py — no PDF fixture needed."""

from figgydeck.clean import clean_caption, split_camel


def test_decodes_ligatures():
    text = "magniﬁcent ﬂowing ﬁeld"
    assert clean_caption(text) == "magnificent flowing field"


def test_strips_running_header():
    text = "Beautiful caption text. BACKGROUND OF THE LABORATORY RAT trailing"
    assert "BACKGROUND" not in clean_caption(text)


def test_strips_footnote_tail():
    text = "Caption body. Names of Donaldson's collaborators are given in parentheses."
    assert "Names of Donaldson" not in clean_caption(text)


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
    assert split_camel("RatStrainsAndStocks") == "Rat Strains And Stocks"


def test_split_camel_idempotent():
    assert split_camel("Already Has Spaces") == "Already Has Spaces"


def test_split_camel_empty():
    assert split_camel("") == ""
