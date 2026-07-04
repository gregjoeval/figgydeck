"""figgydeck: turn textbooks into study decks."""

from figgydeck.anki import build_apkg, build_combined_apkg
from figgydeck.extract import extract_chapter

# NOTE: pptx builders (build_pptx, build_combined_pptx) are intentionally not
# re-exported here — they require the optional python-pptx dependency. Import
# them from figgydeck.pptx directly.

__version__ = "0.2.0"
__all__ = ["extract_chapter", "build_apkg", "build_combined_apkg"]
