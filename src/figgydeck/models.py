"""Lightweight shared data structures and manifest I/O.

Kept dependency-free (stdlib only) so the deck builders in ``figgydeck.anki`` and
``figgydeck.pptx`` can import these without pulling in the heavy extraction stack
(``pdfplumber`` et al.).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Schema version written into manifest.json. Bump when the on-disk shape of a
# manifest entry changes; ``load_manifest`` stays backward compatible.
MANIFEST_VERSION = 1


@dataclass
class Chapter:
    """One chapter's extraction result, passed to the combined deck builders.

    A small typed record (rather than a bare tuple) so the public
    ``build_combined_apkg`` / ``build_combined_pptx`` signatures can gain fields
    later without breaking callers.
    """

    manifest: list[dict] | str | Path  # entries list, or path to a manifest.json
    images_dir: str | Path             # folder holding the referenced images
    title: str                         # chapter display title


def load_manifest(source: list[dict] | str | Path) -> list[dict]:
    """Return the list of manifest entries from any accepted manifest source.

    Accepts an already-loaded entries list (returned unchanged), or a path to a
    ``manifest.json``. Handles both the current ``{"version": N, "entries": [...]}``
    layout and the legacy bare-array format written before the schema was versioned.
    """
    if not isinstance(source, (str, Path)):
        return source
    data = json.loads(Path(source).read_text())
    if isinstance(data, dict):
        return data.get("entries", [])
    return data  # legacy bare array
