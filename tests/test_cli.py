"""CLI argparse surface tests.

Exercises figgydeck.cli.main with mocked extract_chapter and builders so
no PDF or external tooling is required.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from figgydeck import cli


@pytest.fixture
def dummy_pdf(tmp_path):
    p = tmp_path / "dummy.pdf"
    p.touch()
    return p


@pytest.fixture
def base_args(dummy_pdf, tmp_path):
    return [str(dummy_pdf), "--book", "Book", "--chapter", "Ch", "--output", str(tmp_path)]


@pytest.fixture
def mocked_pipeline():
    """Patch extract_chapter and both builders. Yields the three mocks."""
    with patch("figgydeck.extract.extract_chapter", return_value=[]) as ex, \
         patch("figgydeck.anki.build_apkg") as apkg, \
         patch("figgydeck.pptx.build_pptx") as pptx:
        yield ex, apkg, pptx


def test_default_writes_apkg_only(base_args, mocked_pipeline):
    ex, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args)
    assert rc == 0
    apkg.assert_called_once()
    pptx.assert_not_called()
    # extract_chapter called with include_tables=False
    assert ex.call_args.kwargs["include_tables"] is False


def test_out_pptx_only(base_args, mocked_pipeline):
    _, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args + ["--out", "pptx"])
    assert rc == 0
    apkg.assert_not_called()
    pptx.assert_called_once()


def test_out_comma_both(base_args, mocked_pipeline):
    _, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args + ["--out", "apkg,pptx"])
    assert rc == 0
    apkg.assert_called_once()
    pptx.assert_called_once()


def test_out_repeated_both(base_args, mocked_pipeline):
    _, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args + ["--out", "apkg", "--out", "pptx"])
    assert rc == 0
    apkg.assert_called_once()
    pptx.assert_called_once()


def test_out_dedup(base_args, mocked_pipeline):
    _, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args + ["--out", "apkg,apkg"])
    assert rc == 0
    assert apkg.call_count == 1
    pptx.assert_not_called()


def test_out_invalid_format_exits(base_args, mocked_pipeline):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(base_args + ["--out", "junk"])
    assert exc_info.value.code != 0


def test_out_empty_value_exits(base_args, mocked_pipeline):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(base_args + ["--out", ""])
    assert exc_info.value.code != 0


def test_tables_flag_passes_include_tables(base_args, mocked_pipeline):
    ex, _, _ = mocked_pipeline
    rc = cli.main(base_args + ["--tables"])
    assert rc == 0
    assert ex.call_args.kwargs["include_tables"] is True


def test_missing_pdf_returns_nonzero(tmp_path):
    rc = cli.main([
        str(tmp_path / "nope.pdf"),
        "--book", "B", "--chapter", "C", "--output", str(tmp_path),
    ])
    assert rc == 2
