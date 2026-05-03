"""Smoke test: extraction on a known-good chapter.

Requires `tests/fixtures/laboratory_rat_ch1.pdf` — not committed to the repo
because of copyright, but the test verifies the structure of the manifest
the extractor produces when run against it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "laboratory_rat_ch1.pdf"

# Skip if the fixture isn't present (e.g. in CI without the PDF)
pytestmark = pytest.mark.skipif(
    not FIXTURE.exists(),
    reason=f"fixture {FIXTURE.name} not present",
)


@pytest.fixture(scope="module")
def manifest(tmp_path_factory):
    from figgydeck.extract import extract_chapter
    out_dir = tmp_path_factory.mktemp("ch1")
    return extract_chapter(FIXTURE, out_dir, verbose=False), out_dir


def test_finds_all_figures_and_tables(manifest):
    m, _ = manifest
    figures = [e for e in m if e["type"] == "figure"]
    tables = [e for e in m if e["type"] == "table"]
    assert len(figures) == 53, f"expected 53 figures, got {len(figures)}"
    assert len(tables) == 2, f"expected 2 tables, got {len(tables)}"


def test_every_figure_has_an_image(manifest):
    m, _ = manifest
    missing = [e["number"] for e in m if e["type"] == "figure" and not e["image_filename"]]
    assert not missing, f"figures without images: {missing}"


def test_every_table_has_an_image(manifest):
    m, _ = manifest
    missing = [e["number"] for e in m if e["type"] == "table" and not e["image_filename"]]
    assert not missing, f"tables without images: {missing}"


def test_critical_swap_cases(manifest):
    """The swap-prone figures whose stream order doesn't match figure order.

    These are the exact cases that defeat naive 'pdfimages -png in order'
    matching. The geometric matcher must get them right.
    """
    m, _ = manifest
    by_num = {e["number"]: e for e in m if e["type"] == "figure"}

    # (figure number, expected image stream index)
    cases = [
        ("1.16", 16),  # apparatus drawings (NOT Watson)
        ("1.17", 15),  # Watson portrait
        ("1.20", 20),  # McCollum feeding device
        ("1.21", 19),  # Osborne portrait
        ("1.23", 23),  # Osborne&Mendel cage
        ("1.24", 22),  # Sherman portrait
        ("1.29", 29),  # Bussey building
        ("1.30", 28),  # Castle's rat cage
        ("1.46", 46),  # Trexler/Reyniers/Ervin photo
        ("1.47", 45),  # flexible film isolators
        ("1.50", 50),  # Kraft portrait
        ("1.51", 49),  # Filter cap design
    ]
    for num, expected_idx in cases:
        actual = by_num[num]["image_filename"]
        expected = f"img-{expected_idx:03d}.png"
        assert actual == expected, f"Fig {num}: expected {expected}, got {actual}"


def test_captions_are_clean(manifest):
    """Captions should not contain running headers, page numbers, or footnote leaks."""
    m, _ = manifest
    for e in m:
        if e["type"] != "figure":
            continue
        cap = e["caption"]
        assert "BACKGROUND OF" not in cap, f"Fig {e['number']} has running-header bleed"
        # ligatures should be decoded
        assert "ﬁ" not in cap, f"Fig {e['number']} has unresolved ligature"
        assert "ﬂ" not in cap, f"Fig {e['number']} has unresolved ligature"


def test_table_titles_present(manifest):
    m, _ = manifest
    for e in m:
        if e["type"] == "table":
            assert e["title"], f"Table {e['number']} has no title"


def test_apkg_round_trip(manifest, tmp_path):
    """Build an apkg from the manifest and verify it's a valid Anki package."""
    import sqlite3
    import zipfile

    from figgydeck.anki import build_apkg

    m, out_dir = manifest
    apkg_path = tmp_path / "ch1.apkg"
    build_apkg(
        m, out_dir / "images",
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
        # 53 figures + 2 tables = 55
        assert n_notes == 55, f"expected 55 notes, got {n_notes}"
