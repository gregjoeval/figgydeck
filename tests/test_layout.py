"""Unit tests for layout.py geometry helpers — no PDF fixture needed."""

from figgydeck.layout import column_of, image_columns


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
