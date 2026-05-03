"""figgydeck: turn textbooks into study decks."""

from figgydeck.anki import build_apkg
from figgydeck.extract import extract_chapter

__version__ = "0.1.0"
__all__ = ["extract_chapter", "build_apkg"]
