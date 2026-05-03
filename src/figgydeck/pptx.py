"""PowerPoint deck builder (optional output format).

This is a thin minimal builder. The richer pptx layout used in early figgydeck
prototypes is preserved in `examples/build_pptx_styled.py` for reference.
"""

from __future__ import annotations

import json
from pathlib import Path


def build_pptx(
    manifest: list[dict] | str | Path,
    images_dir: str | Path,
    book_title: str,
    chapter_title: str,
    output_path: str | Path,
    *,
    verbose: bool = True,
) -> Path:
    """Build a slide deck where each figure/table gets one slide.

    Each slide:
        - Image centered
        - Caption text in speaker notes (so the slide face stays minimal
          for visual recall)
    """
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
    except ImportError as e:
        raise ImportError(
            "build_pptx requires python-pptx. Install with: pip install figgydeck[pptx]"
        ) from e

    if isinstance(manifest, (str, Path)):
        manifest = json.loads(Path(manifest).read_text())

    images_dir = Path(images_dir)
    output_path = Path(output_path)
    log = print if verbose else (lambda *a, **k: None)

    pres = Presentation()
    pres.slide_width = Inches(13.333)
    pres.slide_height = Inches(7.5)
    blank_layout = pres.slide_layouts[6]  # blank

    # Title slide
    title_slide = pres.slides.add_slide(blank_layout)
    txt = title_slide.shapes.add_textbox(
        Inches(1), Inches(2.5), Inches(11.3), Inches(2.5)
    )
    p = txt.text_frame.paragraphs[0]
    p.text = book_title
    p.runs[0].font.size = Pt(36)
    p.runs[0].font.bold = True
    p2 = txt.text_frame.add_paragraph()
    p2.text = chapter_title
    p2.runs[0].font.size = Pt(24)

    # Figure / table slides
    added = 0
    skipped = 0
    for entry in manifest:
        if not entry.get("image_filename"):
            skipped += 1
            continue
        img_path = images_dir / entry["image_filename"]
        if not img_path.exists():
            skipped += 1
            continue

        slide = pres.slides.add_slide(blank_layout)

        # Image — fit to slide with reasonable margins
        slide.shapes.add_picture(
            str(img_path),
            Inches(1), Inches(0.75),
            width=Inches(11.3), height=Inches(6),
        )

        # Speaker notes carry the study content (title, caption, source)
        kind = entry["type"].capitalize()
        number_label = f"Table {entry['number']}" if kind == "Table" else f"Figure {entry['number']}"
        notes_lines = [
            f"{number_label}",
        ]
        if entry.get("title"):
            notes_lines.append(entry["title"])
        if entry.get("caption"):
            notes_lines.append("")
            notes_lines.append(entry["caption"])
        notes_lines.extend([
            "",
            f"Book: {book_title}",
            f"Chapter: {chapter_title}",
            f"Page: {entry['page']}",
        ])
        slide.notes_slide.notes_text_frame.text = "\n".join(notes_lines)
        added += 1

    pres.save(str(output_path))
    log(f"\nWrote: {output_path}")
    log(f"  slides added: {added}")
    log(f"  skipped: {skipped}")
    return output_path
