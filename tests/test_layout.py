"""Unit tests for layout.py geometry helpers — no PDF fixture needed."""

import pytest

from figgydeck.layout import column_of, image_columns, parse_labels


def test_column_of_left():
    assert column_of(100, 612) == 0


def test_column_of_right():
    assert column_of(400, 612) == 1


def test_column_of_midline():
    # Exactly at midline should be in the right column (consistent with our convention)
    # Anything < width/2 is left, >= width/2 is right
    assert column_of(305, 612) == 0
    assert column_of(306, 612) == 1


def test_image_columns_left_only():
    img = {"x0": 50, "x1": 250}
    assert image_columns(img, 612) == {0}


def test_image_columns_right_only():
    img = {"x0": 350, "x1": 550}
    assert image_columns(img, 612) == {1}


def test_image_columns_spans_both():
    """Wide images (e.g. full-page-width figures) span both columns."""
    img = {"x0": 100, "x1": 500}
    assert image_columns(img, 612) == {0, 1}


# --- label parsing: figure/table labels across publisher styles -------------
# raw_lines are (text, x, y); parse_labels runs on lines already filtered to
# the 9pt label size by extract_page, so it should recognize the label keyword
# regardless of case (Elsevier uppercase "FIGURE" vs Wiley title-case "Figure").

@pytest.mark.parametrize("text,kind,number", [
    ("FIGURE 1.2 Some caption", "figure", "1.2"),        # Elsevier uppercase
    ("Figure 1.2 Some caption", "figure", "1.2"),        # Wiley title-case
    ("Figure2.2.5 Glued number", "figure", "2.2.5"),     # Wiley number-glued
    ("TABLE 3.1 A table title", "table", "3.1"),
    ("Table 3.1 A table title", "table", "3.1"),
])
def test_parse_labels_matches_case_insensitively(text, kind, number):
    labels = parse_labels([(text, 100.0, 50.0)], page_width=612)
    assert len(labels) == 1
    assert labels[0].kind == kind
    assert labels[0].number == number


def test_parse_labels_ignores_non_label_lines():
    labels = parse_labels([("This paragraph merely mentions a figure.", 100.0, 50.0)],
                          page_width=612)
    assert labels == []
