"""Tests for build_combined_apkg — one .apkg with per-chapter subdecks.

The key correctness concern: images from different chapters can share a
basename (e.g. img-000.png). genanki keys media by basename, so the combined
builder must namespace them or one would clobber the other.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

from PIL import Image

from figgydeck import Chapter
from figgydeck.anki import build_combined_apkg


def _png(path: Path, color) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), color).save(path)


def _chapter(images_dir: Path, number: str, color) -> list[dict]:
    _png(images_dir / "img-000.png", color)
    return [{
        "number": number, "type": "figure", "title": None,
        "caption": f"caption {number}", "page": 1, "image_filename": "img-000.png",
    }]


def test_combined_apkg_namespaces_colliding_media(tmp_path):
    # Two chapters, both with an image literally named img-000.png.
    ch1_imgs = tmp_path / "ch1" / "images"
    ch2_imgs = tmp_path / "ch2" / "images"
    m1 = _chapter(ch1_imgs, "1.1", (200, 30, 30))
    m2 = _chapter(ch2_imgs, "2.1", (30, 30, 200))

    out = tmp_path / "combined.apkg"
    build_combined_apkg(
        [Chapter(m1, ch1_imgs, "Chapter 1"), Chapter(m2, ch2_imgs, "Chapter 2")],
        "Book", out, verbose=False,
    )

    assert out.exists()
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert "collection.anki2" in names
        # genanki stores a `media` json mapping "0","1",... -> original basename
        media_map = json.loads(z.read("media"))
        # two distinct media files, no basename collision
        assert len(media_map) == 2
        assert len(set(media_map.values())) == 2

        data = z.read("collection.anki2")
    db = tmp_path / "collection.anki2"
    db.write_bytes(data)
    conn = sqlite3.connect(db)
    try:
        n_notes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        # one note per chapter
        assert n_notes == 2
        # two subdecks nested under the book (names use "::" separator)
        col = conn.execute("SELECT decks FROM col").fetchone()
        if col and col[0]:  # older schema stores decks JSON on the col row
            deck_names = {d["name"] for d in json.loads(col[0]).values()}
            assert any("Book::Chapter 1" == n for n in deck_names)
            assert any("Book::Chapter 2" == n for n in deck_names)
    finally:
        conn.close()


def test_deck_id_is_deterministic():
    """deck_id must be stable across runs (regression guard: an earlier impl used
    builtin hash(), which is salted per process via PYTHONHASHSEED)."""
    from figgydeck.anki import _deck_for
    # Depends only on book + chapter, not the deck's display name.
    a = _deck_for("Book", "Chapter 1", "Book::Chapter 1")
    b = _deck_for("Book", "Chapter 1", "a different display name")
    assert a.deck_id == b.deck_id == 2059439393
