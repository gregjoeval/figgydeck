"""manifest.json schema versioning and the load_manifest helper."""

from __future__ import annotations

import json

from figgydeck.models import MANIFEST_VERSION, load_manifest


def _entry(number="1.1"):
    return {
        "number": number, "type": "figure", "title": None,
        "caption": "c", "page": 1, "image_filename": "img-000.png",
    }


def test_load_manifest_passthrough_list():
    entries = [_entry()]
    # An already-loaded entries list is returned unchanged.
    assert load_manifest(entries) is entries


def test_load_versioned_file(tmp_path):
    entries = [_entry("1.1"), _entry("1.2")]
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"version": MANIFEST_VERSION, "entries": entries}))
    assert load_manifest(p) == entries
    assert load_manifest(str(p)) == entries  # str path too


def test_load_legacy_bare_array(tmp_path):
    # Manifests written before the schema was versioned were a bare JSON array.
    entries = [_entry()]
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(entries))
    assert load_manifest(p) == entries
