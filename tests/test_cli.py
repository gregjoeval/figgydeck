"""CLI argparse surface tests.

Exercises figgydeck.cli.main with mocked extract_chapter and builders so
no PDF or external tooling is required.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
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
    # No --format here; individual tests add it (it is required).
    return [str(dummy_pdf), "--book", "Book", "--chapter", "Ch", "--output", str(tmp_path)]


@pytest.fixture
def mocked_pipeline():
    """Patch extract_chapter and both builders. Yields the three mocks."""
    with patch("figgydeck.extract.extract_chapter", return_value=[]) as ex, \
         patch("figgydeck.anki.build_apkg") as apkg, \
         patch("figgydeck.pptx.build_pptx") as pptx:
        yield ex, apkg, pptx


def test_format_is_required(base_args, mocked_pipeline):
    _, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args)  # no --format
    assert rc == 2
    apkg.assert_not_called()
    pptx.assert_not_called()


def test_format_apkg_only(base_args, mocked_pipeline):
    ex, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args + ["--format", "apkg"])
    assert rc == 0
    apkg.assert_called_once()
    pptx.assert_not_called()
    # extract_chapter called with include_tables=False
    assert ex.call_args.kwargs["include_tables"] is False


def test_format_pptx_only(base_args, mocked_pipeline):
    _, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args + ["--format", "pptx"])
    assert rc == 0
    apkg.assert_not_called()
    pptx.assert_called_once()


def test_format_short_flag(base_args, mocked_pipeline):
    _, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args + ["-f", "pptx"])
    assert rc == 0
    pptx.assert_called_once()


def test_format_comma_both(base_args, mocked_pipeline):
    _, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args + ["--format", "apkg,pptx"])
    assert rc == 0
    apkg.assert_called_once()
    pptx.assert_called_once()


def test_format_repeated_both(base_args, mocked_pipeline):
    _, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args + ["--format", "apkg", "--format", "pptx"])
    assert rc == 0
    apkg.assert_called_once()
    pptx.assert_called_once()


def test_format_dedup(base_args, mocked_pipeline):
    _, apkg, pptx = mocked_pipeline
    rc = cli.main(base_args + ["--format", "apkg,apkg"])
    assert rc == 0
    assert apkg.call_count == 1
    pptx.assert_not_called()


def test_format_invalid_value_exits(base_args, mocked_pipeline):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(base_args + ["--format", "junk"])
    assert exc_info.value.code != 0


def test_format_empty_value_exits(base_args, mocked_pipeline):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(base_args + ["--format", ""])
    assert exc_info.value.code != 0


def test_tables_flag_passes_include_tables(base_args, mocked_pipeline):
    ex, _, _ = mocked_pipeline
    rc = cli.main(base_args + ["--format", "apkg", "--tables"])
    assert rc == 0
    assert ex.call_args.kwargs["include_tables"] is True


def test_missing_pdf_returns_nonzero(tmp_path):
    rc = cli.main([
        str(tmp_path / "nope.pdf"),
        "--book", "B", "--chapter", "C", "--format", "apkg", "--output", str(tmp_path),
    ])
    assert rc == 2


# --- extraction artifacts are opt-in ----------------------------------------

def _fake_extract(pdf, out_dir, *, include_tables=False, verbose=True):
    """Stand-in for extract_chapter that writes the intermediate artifacts."""
    out_dir = Path(out_dir)
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    (out_dir / "images" / "img-000.png").write_bytes(b"\x89PNG")
    (out_dir / "manifest.json").write_text('{"version": 1, "entries": []}')
    return []


def test_artifacts_not_emitted_by_default(base_args, tmp_path):
    with patch("figgydeck.extract.extract_chapter", side_effect=_fake_extract), \
         patch("figgydeck.anki.build_apkg"):
        rc = cli.main(base_args + ["--format", "apkg"])
    assert rc == 0
    assert not (tmp_path / "manifest.json").exists()
    assert not (tmp_path / "images").exists()


def test_save_manifest_and_images_emit_artifacts(base_args, tmp_path):
    with patch("figgydeck.extract.extract_chapter", side_effect=_fake_extract), \
         patch("figgydeck.anki.build_apkg"):
        rc = cli.main(base_args + ["--format", "apkg", "--save-manifest", "--save-images"])
    assert rc == 0
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "images" / "img-000.png").exists()


# --- multi-PDF, --combine, and title resolution -----------------------------

@pytest.fixture
def two_pdfs(tmp_path):
    a = tmp_path / "ch01.pdf"
    a.touch()
    b = tmp_path / "ch02.pdf"
    b.touch()
    return a, b


@pytest.fixture
def mocked_all(tmp_path):
    """Patch extract + all four builders (single and combined). Yields a ns."""
    with patch("figgydeck.extract.extract_chapter", return_value=[]) as ex, \
         patch("figgydeck.anki.build_apkg") as apkg, \
         patch("figgydeck.pptx.build_pptx") as pptx, \
         patch("figgydeck.anki.build_combined_apkg") as capkg, \
         patch("figgydeck.pptx.build_combined_pptx") as cpptx:
        yield SimpleNamespace(ex=ex, apkg=apkg, pptx=pptx, capkg=capkg, cpptx=cpptx)


def test_combine_writes_one_artifact_per_format(two_pdfs, tmp_path, mocked_all):
    a, b = two_pdfs
    rc = cli.main([
        str(a), str(b), "--book", "Book", "--combine",
        "--format", "apkg,pptx", "--output", str(tmp_path),
    ])
    assert rc == 0
    mocked_all.capkg.assert_called_once()
    mocked_all.cpptx.assert_called_once()
    # single-chapter builders must not run in combine mode
    mocked_all.apkg.assert_not_called()
    mocked_all.pptx.assert_not_called()
    # combined builders receive Chapter records
    (chapters, *_rest) = mocked_all.capkg.call_args.args
    assert all(isinstance(c, cli.Chapter) for c in chapters)


def test_multi_pdf_without_combine_writes_one_per_pdf(two_pdfs, tmp_path, mocked_all):
    a, b = two_pdfs
    rc = cli.main([
        str(a), str(b), "--book", "Book", "--format", "pptx", "--output", str(tmp_path),
    ])
    assert rc == 0
    assert mocked_all.pptx.call_count == 2
    mocked_all.cpptx.assert_not_called()


def test_titles_derived_from_filename(two_pdfs, tmp_path, mocked_all):
    a, b = two_pdfs
    rc = cli.main([
        str(a), str(b), "--book", "Book", "--format", "pptx", "--output", str(tmp_path),
    ])
    assert rc == 0
    # build_pptx(manifest, images_dir, book, chapter, output, ...)
    titles = [call.args[3] for call in mocked_all.pptx.call_args_list]
    assert titles == ["Chapter 1", "Chapter 2"]


def test_explicit_chapters_are_paired_in_order(two_pdfs, tmp_path, mocked_all):
    a, b = two_pdfs
    rc = cli.main([
        str(a), str(b), "--book", "Book",
        "--chapter", "Intro", "--chapter", "Methods",
        "--format", "pptx", "--output", str(tmp_path),
    ])
    assert rc == 0
    titles = [call.args[3] for call in mocked_all.pptx.call_args_list]
    assert titles == ["Intro", "Methods"]


@pytest.mark.parametrize("filename,expected", [
    ("ch01.pdf", "Chapter 1"),
    ("ch10.pdf", "Chapter 10"),
    ("Chapter-3-Biology-and-Diseases-of-Mice_.pdf", "Chapter 3: Biology and Diseases of Mice"),
    ("Chapter-11 - Microbiological Quality Control.pdf", "Chapter 11: Microbiological Quality Control"),
    ("intro.pdf", "Intro"),
])
def test_chapter_title_derivation(filename, expected):
    assert cli._chapter_title(Path(filename), None) == expected


def test_chapter_count_mismatch_errors(two_pdfs, tmp_path, mocked_all):
    a, b = two_pdfs
    rc = cli.main([
        str(a), str(b), "--book", "Book", "--chapter", "OnlyOne",
        "--format", "pptx", "--output", str(tmp_path),
    ])
    assert rc == 2
    mocked_all.pptx.assert_not_called()
    mocked_all.cpptx.assert_not_called()
