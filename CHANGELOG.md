# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0]

First stable public release on PyPI: `pip install figgydeck`.

Because this is the 1.0 line, the CLI and public Python API are now covered by
semver. Compared to the pre-release code, the following are **breaking**:

### Changed
- CLI: the format selector `--out` is renamed to `--format` / `-f`, and is now
  **required** — there is no default output format. Running without it exits
  with a non-zero status and a message listing the choices.
- CLI: the output directory now contains only the built deck(s) by default. The
  extracted `manifest.json` and `images/` are no longer written there unless you
  pass the new `--save-manifest` / `--save-images` flags.
- `manifest.json` gained a schema wrapper: `{"version": 1, "entries": [...]}`
  instead of a bare array. `figgydeck` still reads legacy bare-array manifests.
- Public API: `build_combined_apkg` and `build_combined_pptx` now take a list of
  `Chapter` objects (`figgydeck.Chapter`) instead of `(manifest, images_dir,
  title)` tuples.

### Fixed
- Anki deck IDs are now derived with a stable SHA-256 digest instead of the
  builtin `hash()` (which is salted per process), so re-running `figgydeck`
  produces the same deck ID and re-imports no longer risk duplicate decks.

### Added
- `--save-manifest` / `--save-images` flags to opt into keeping the extraction
  intermediates.
- `figgydeck.Chapter` is exported from the top-level package.
