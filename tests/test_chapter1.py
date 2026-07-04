"""Smoke test: extraction on a real chapter PDF you supply.

Requires `tests/fixtures/sample_chapter.pdf` — not committed to the repo (never
commit copyrighted material). When present, the test checks the structural
invariants of the manifest the extractor produces; it skips otherwise, so CI and
public checkouts pass without the PDF.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "sample_chapter.pdf"

# Skip if the fixture isn't present (e.g. in CI without the PDF)
pytestmark = pytest.mark.skipif(
    not FIXTURE.exists(),
    reason=f"fixture {FIXTURE.name} not present",
)

# A run of >= 3 consecutive all-caps words signals a running-header bleed.
_HEADER_BLEED = re.compile(r"[A-Z][A-Z&.'-]+(?:\s+[A-Z][A-Z&.'-]+){2,}")


@pytest.fixture(scope="module")
def manifest_with_tables(tmp_path_factory):
    from figgydeck.extract import extract_chapter
    out_dir = tmp_path_factory.mktemp("chapter")
    return extract_chapter(FIXTURE, out_dir, include_tables=True, verbose=False), out_dir


def test_finds_figures(manifest_with_tables):
    m, _ = manifest_with_tables
    figures = [e for e in m if e["type"] == "figure"]
    assert figures, "expected at least one figure in the manifest"


def test_every_figure_has_an_image(manifest_with_tables):
    m, _ = manifest_with_tables
    missing = [e["number"] for e in m if e["type"] == "figure" and not e["image_filename"]]
    assert not missing, f"figures without images: {missing}"


def test_every_table_has_an_image(manifest_with_tables):
    m, _ = manifest_with_tables
    missing = [e["number"] for e in m if e["type"] == "table" and not e["image_filename"]]
    assert not missing, f"tables without images: {missing}"


def test_figure_images_are_distinct(manifest_with_tables):
    """Each figure must map to its own image — no two figures share one file.

    This is the invariant the geometric matcher exists to protect: naive
    'Nth image is figure N' ordering collapses swap-prone pairs onto the wrong
    (and sometimes duplicate) images.
    """
    m, _ = manifest_with_tables
    imgs = [e["image_filename"] for e in m if e["type"] == "figure" and e["image_filename"]]
    dupes = {x for x in imgs if imgs.count(x) > 1}
    assert not dupes, f"multiple figures share an image: {sorted(dupes)}"


def test_default_skips_tables(tmp_path):
    """Without include_tables, tables should be excluded from the manifest entirely."""
    from figgydeck.extract import extract_chapter
    m = extract_chapter(FIXTURE, tmp_path, verbose=False)
    assert not any(e["type"] == "table" for e in m), \
        "default extraction must not include tables"
    # Sanity check: figures still come through.
    assert any(e["type"] == "figure" for e in m)


def test_captions_are_clean(manifest_with_tables):
    """Captions should not contain running-header or footnote leaks."""
    m, _ = manifest_with_tables
    for e in m:
        if e["type"] != "figure":
            continue
        cap = e["caption"]
        assert not _HEADER_BLEED.search(cap), f"Fig {e['number']} has running-header bleed"
        # ligatures should be decoded
        assert "ﬁ" not in cap, f"Fig {e['number']} has unresolved ligature"
        assert "ﬂ" not in cap, f"Fig {e['number']} has unresolved ligature"


def test_table_titles_present(manifest_with_tables):
    m, _ = manifest_with_tables
    for e in m:
        if e["type"] == "table":
            assert e["title"], f"Table {e['number']} has no title"


def test_apkg_round_trip(manifest_with_tables, tmp_path):
    """Build an apkg from a figs-only manifest view and verify it's a valid Anki package.

    Uses the figs-only view to exercise the default behavior end-to-end:
    manifest filtered to figures -> apkg with figures only.
    """
    import sqlite3
    import zipfile

    from figgydeck.anki import build_apkg

    m, out_dir = manifest_with_tables
    figs_only = [e for e in m if e["type"] == "figure"]
    apkg_path = tmp_path / "chapter.apkg"
    build_apkg(
        figs_only, out_dir / "images",
        "Test Book", "Test Chapter",
        apkg_path, verbose=False,
    )

    assert apkg_path.exists()
    assert apkg_path.stat().st_size > 1024  # not empty

    with zipfile.ZipFile(apkg_path) as z:
        assert "collection.anki2" in z.namelist()
        # extract the sqlite db and check note count
        with z.open("collection.anki2") as f:
            data = f.read()
        sqlite_path = tmp_path / "collection.anki2"
        sqlite_path.write_bytes(data)
        conn = sqlite3.connect(sqlite_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM notes")
        n_notes = c.fetchone()[0]
        # one note per figure
        assert n_notes == len(figs_only), f"expected {len(figs_only)} notes, got {n_notes}"
