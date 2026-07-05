"""figgydeck: turn textbooks into study decks (PowerPoint slides or Anki decks)."""

from figgydeck.anki import build_apkg, build_combined_apkg
from figgydeck.extract import extract_chapter

# The PowerPoint builders (build_pptx, build_combined_pptx) are equal
# first-class outputs, but they live in figgydeck.pptx and are imported from
# there so that the top-level package never hard-imports the optional
# python-pptx dependency. Use `from figgydeck.pptx import build_pptx`.

__version__ = "0.2.0"
__all__ = ["extract_chapter", "build_apkg", "build_combined_apkg"]
