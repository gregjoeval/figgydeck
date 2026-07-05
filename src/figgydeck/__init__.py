"""figgydeck: turn textbooks into study decks (PowerPoint slides or Anki decks)."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from figgydeck.anki import build_apkg, build_combined_apkg
from figgydeck.extract import extract_chapter
from figgydeck.models import Chapter

# The PowerPoint builders (build_pptx, build_combined_pptx) are equal
# first-class outputs, but they live in figgydeck.pptx and are imported from
# there so that the top-level package never hard-imports the optional
# python-pptx dependency. Use `from figgydeck.pptx import build_pptx`.

# Version is defined once in pyproject.toml; read it back from the installed
# distribution metadata so the two can never drift.
try:
    __version__ = _pkg_version("figgydeck")
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "0.0.0+unknown"

__all__ = ["extract_chapter", "build_apkg", "build_combined_apkg", "Chapter"]
