"""Anki deck builder: turn a manifest + images into a .apkg file."""

from __future__ import annotations

import html
import json
import re
import shutil
import tempfile
from pathlib import Path

import genanki

# Stable model ID — must not change between runs, or Anki will fail to
# update existing notes when users re-import.
_MODEL_ID = 1607392319
_DECK_ID_BASE = 2059400110


CARD_CSS = """
/* ---------- Light mode (default) ---------- */
.card {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 17px; color: #2A1B23; background: #F8F4EC;
  text-align: left; padding: 18px; line-height: 1.5;
}
.card-img {
  display: block; max-width: 100%; max-height: 60vh;
  margin: 0 auto 12px; border-radius: 6px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
  background: #ffffff; padding: 6px;
}
.tag-row {
  text-align: center; font-size: 12px; letter-spacing: 2px;
  text-transform: uppercase; color: #A26769;
  font-weight: 600; margin-top: 8px;
}
.divider {
  border: 0; border-top: 2px solid #C9A86A;
  width: 60px; margin: 16px auto;
}
.label {
  font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase;
  color: #A26769; font-weight: 600; margin-bottom: 4px;
}
.title {
  font-family: Georgia, serif; font-size: 22px; font-weight: 700;
  color: #6D2E46; margin: 0 0 14px 0; line-height: 1.3;
}
.caption { font-size: 15px; color: #2A1B23; margin: 0 0 16px 0; }
.meta {
  font-size: 12px; color: #8A7079; font-style: italic;
  border-top: 1px solid #D8C9B5; padding-top: 10px; margin-top: 12px;
}
.meta-line { margin: 2px 0; }
.meta b { color: #6D2E46; font-style: normal; }

/* ---------- Dark mode (.nightMode / .night_mode) ---------- */
.nightMode .card, .night_mode .card,
.card.nightMode, .card.night_mode {
  color: #ECE2D0; background: #1F1419;
}
.nightMode .card-img, .night_mode .card-img,
.card.nightMode .card-img, .card.night_mode .card-img {
  background: #ffffff; box-shadow: 0 2px 16px rgba(0,0,0,0.6);
}
.nightMode .tag-row, .night_mode .tag-row,
.card.nightMode .tag-row, .card.night_mode .tag-row { color: #E8B86F; }
.nightMode .divider, .night_mode .divider,
.card.nightMode .divider, .card.night_mode .divider { border-top-color: #E8B86F; }
.nightMode .label, .night_mode .label,
.card.nightMode .label, .card.night_mode .label { color: #E8B86F; }
.nightMode .title, .night_mode .title,
.card.nightMode .title, .card.night_mode .title { color: #F2C9A0; }
.nightMode .caption, .night_mode .caption,
.card.nightMode .caption, .card.night_mode .caption { color: #ECE2D0; }
.nightMode .meta, .night_mode .meta,
.card.nightMode .meta, .card.night_mode .meta {
  color: #B5A39A; border-top-color: #4A2D38;
}
.nightMode .meta b, .night_mode .meta b,
.card.nightMode .meta b, .card.night_mode .meta b { color: #F2C9A0; }
"""


def _build_model() -> genanki.Model:
    return genanki.Model(
        _MODEL_ID,
        "figgydeck Card",
        fields=[
            {"name": "Number"},   # "Fig X.Y" or "Tab X.Y"
            {"name": "Image"},    # <img src="...">
            {"name": "Title"},    # tables have one; figures may be empty
            {"name": "Caption"},  # cleaned caption body
            {"name": "Book"},
            {"name": "Chapter"},
            {"name": "Page"},
            {"name": "Type"},     # "Figure" | "Table"
        ],
        templates=[{
            "name": "Image -> Details",
            "qfmt": '{{Image}}<div class="tag-row">{{Number}}</div>',
            "afmt": (
                '{{Image}}<div class="tag-row">{{Number}}</div>'
                '<hr class="divider">'
                '<div class="label">{{Type}}</div>'
                '{{#Title}}<div class="title">{{Title}}</div>{{/Title}}'
                '{{#Caption}}<div class="caption">{{Caption}}</div>{{/Caption}}'
                '<div class="meta">'
                '<div class="meta-line"><b>Book:</b> {{Book}}</div>'
                '<div class="meta-line"><b>Chapter:</b> {{Chapter}}</div>'
                '<div class="meta-line"><b>Page:</b> {{Page}}</div>'
                '</div>'
            ),
        }],
        css=CARD_CSS,
    )


def _slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s


def _add_notes(
    deck: genanki.Deck,
    model: genanki.Model,
    manifest: list[dict],
    images_dir: Path,
    book_title: str,
    chapter_title: str,
    media_files: list[str],
    *,
    media_prefix: str = "",
    stage_dir: Path | None = None,
    log=lambda *a, **k: None,
) -> int:
    """Add one note per figure/table entry to `deck`; return the skipped count.

    Appends each referenced image path to `media_files` (the caller writes them
    into the genanki Package). genanki keys media by basename, so when merging
    several chapters into one package `media_prefix` (the chapter slug) is set:
    each image is copied into `stage_dir` as ``f"{media_prefix}__{name}"`` and
    the note's ``<img src>`` references that unique basename. With an empty
    prefix (single-chapter build) images are referenced in place, unchanged.
    """
    book_tag = _slugify(book_title)
    chapter_tag = _slugify(chapter_title)
    skipped = 0

    for entry in manifest:
        if not entry.get("image_filename"):
            log(f"  skip {entry['type']} {entry['number']}: no image")
            skipped += 1
            continue
        img_path = images_dir / entry["image_filename"]
        if not img_path.exists():
            log(f"  skip {entry['type']} {entry['number']}: missing {img_path}")
            skipped += 1
            continue

        if media_prefix:
            if stage_dir is None:
                raise ValueError("media_prefix requires stage_dir")
            media_name = f"{media_prefix}__{img_path.name}"
            staged = stage_dir / media_name
            shutil.copy(img_path, staged)
            media_files.append(str(staged))
        else:
            media_name = img_path.name
            media_files.append(str(img_path))

        kind = entry["type"].capitalize()
        number_label = f"Tab {entry['number']}" if kind == "Table" else f"Fig {entry['number']}"

        note = genanki.Note(
            model=model,
            fields=[
                number_label,
                f'<img class="card-img" src="{html.escape(media_name)}">',
                html.escape(entry.get("title") or ""),
                html.escape(entry.get("caption") or ""),
                html.escape(book_title),
                html.escape(chapter_title),
                f"p. {entry['page']}",
                kind,
            ],
            tags=[
                f"book::{book_tag}",
                f"chapter::{chapter_tag}",
                f"type::{kind.lower()}",
            ],
            # Stable GUID: re-running figgydeck and re-importing into Anki
            # updates existing notes rather than creating duplicates.
            guid=genanki.guid_for(book_tag, chapter_tag, kind, entry["number"]),
        )
        deck.add_note(note)

    return skipped


def _deck_for(book_title: str, chapter_title: str, deck_name: str) -> genanki.Deck:
    """Create a genanki.Deck with a stable-ish id derived from book+chapter.

    NOTE: builtin hash() is not stable across processes (PYTHONHASHSEED), so the
    deck id can vary between runs. Anki keys decks by name on import, so this is
    cosmetic; kept as-is for backward compatibility with existing decks.
    """
    book_tag = _slugify(book_title)
    chapter_tag = _slugify(chapter_title)
    deck_id = _DECK_ID_BASE + abs(hash(f"{book_tag}::{chapter_tag}")) % 100000
    return genanki.Deck(deck_id, deck_name)


def build_apkg(
    manifest: list[dict] | str | Path,
    images_dir: str | Path,
    book_title: str,
    chapter_title: str,
    output_path: str | Path,
    *,
    verbose: bool = True,
) -> Path:
    """Build an Anki .apkg from a chapter manifest.

    Args:
        manifest: Either the manifest list (from `extract_chapter()`) or a
            path to a `manifest.json` file.
        images_dir: Folder containing the extracted images referenced in
            the manifest.
        book_title: Display title for the book — appears on every card back.
        chapter_title: Display title for the chapter.
        output_path: Where to write the `.apkg` file.

    Returns:
        Path to the written .apkg file.
    """
    if isinstance(manifest, (str, Path)):
        manifest = json.loads(Path(manifest).read_text())

    images_dir = Path(images_dir)
    output_path = Path(output_path)
    log = print if verbose else (lambda *a, **k: None)

    deck = _deck_for(book_title, chapter_title, f"{book_title} :: {chapter_title}")
    model = _build_model()
    media_files: list[str] = []

    skipped = _add_notes(
        deck, model, manifest, images_dir, book_title, chapter_title,
        media_files, log=log,
    )

    pkg = genanki.Package(deck)
    pkg.media_files = media_files
    pkg.write_to_file(str(output_path))

    log(f"\nWrote: {output_path}")
    log(f"  notes added: {len(deck.notes)}")
    log(f"  skipped: {skipped}")

    return output_path


def build_combined_apkg(
    chapters: list[tuple[list[dict], Path, str]],
    book_title: str,
    output_path: str | Path,
    *,
    verbose: bool = True,
) -> Path:
    """Build one `.apkg` merging every chapter into its own Anki subdeck.

    Args:
        chapters: list of (manifest, images_dir, chapter_title). Each manifest
            may be the list from `extract_chapter()` or a path to a
            `manifest.json`.
        book_title: Book title — the parent deck; each chapter becomes a
            subdeck named ``"{book_title}::{chapter_title}"`` ("::" with no
            spaces is Anki's subdeck separator, so they nest under the book).
        output_path: Where to write the combined `.apkg`.

    Images from different chapters can share a basename (e.g. ``img-000.png``);
    since genanki keys media by basename, each chapter's images are staged with
    a chapter-prefixed basename so they don't collide inside the package.
    """
    output_path = Path(output_path)
    log = print if verbose else (lambda *a, **k: None)

    model = _build_model()
    decks: list[genanki.Deck] = []
    media_files: list[str] = []

    # Keep the staging dir alive until after the package is written.
    with tempfile.TemporaryDirectory(prefix="figgydeck-apkg-") as tmp:
        stage_dir = Path(tmp)
        total_notes = 0
        total_skipped = 0

        for i, (manifest, images_dir, chapter_title) in enumerate(chapters):
            if isinstance(manifest, (str, Path)):
                manifest = json.loads(Path(manifest).read_text())
            deck = _deck_for(
                book_title, chapter_title, f"{book_title}::{chapter_title}"
            )
            # Index-prefixed so media basenames stay unique even if two
            # chapters share a title (and thus a slug).
            skipped = _add_notes(
                deck, model, manifest, Path(images_dir), book_title, chapter_title,
                media_files, media_prefix=f"ch{i}-{_slugify(chapter_title)}",
                stage_dir=stage_dir, log=log,
            )
            decks.append(deck)
            total_notes += len(deck.notes)
            total_skipped += skipped

        pkg = genanki.Package(decks)
        pkg.media_files = media_files
        pkg.write_to_file(str(output_path))

    log(f"\nWrote: {output_path}")
    log(f"  chapters: {len(chapters)}")
    log(f"  notes added: {total_notes}")
    log(f"  skipped: {total_skipped}")

    return output_path
