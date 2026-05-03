"""Image extraction: pull figures from a PDF (via pdfimages) and crop tables
from rasterized pages.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def extract_embedded_images(pdf_path: Path, out_dir: Path) -> dict[int, list[int]]:
    """Run `pdfimages` to extract every embedded bitmap image.

    Returns a mapping from 1-based page number to a list of global stream
    indices on that page. The caller can use this to know which extracted
    image file (img-NNN.png) corresponds to the Nth image on a given page.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdfimages", "-png", str(pdf_path), str(out_dir / "img")],
        check=True, capture_output=True,
    )

    listing = subprocess.run(
        ["pdfimages", "-list", str(pdf_path)],
        check=True, capture_output=True, text=True,
    ).stdout

    page_to_streams: dict[int, list[int]] = {}
    stream_idx = 0
    for line in listing.splitlines()[2:]:
        parts = line.split()
        if len(parts) < 2 or not parts[0].isdigit():
            continue
        pnum = int(parts[0])
        page_to_streams.setdefault(pnum, []).append(stream_idx)
        stream_idx += 1

    return page_to_streams


def stream_index_to_filename(stream_idx: int, total_streams: int) -> str:
    """pdfimages pads the filename based on total page count. Match its scheme."""
    pad = max(3, len(str(total_streams - 1)))
    return f"img-{stream_idx:0{pad}d}.png"


def render_table_image(
    pdf_path: Path,
    page_num: int,
    bbox_pts: tuple[float, float, float, float],
    page_size_pts: tuple[float, float],
    output_path: Path,
    dpi: int = 200,
) -> bool:
    """Rasterize a single page and crop the table region.

    Args:
        bbox_pts: (x0, y0, x1, y1) in PDF points, top-left origin
        page_size_pts: (width, height) of source PDF page in points
    """
    from PIL import Image  # local import: keep module import-light

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi),
             "-f", str(page_num), "-l", str(page_num),
             str(pdf_path), str(td_path / "page")],
            check=True, capture_output=True,
        )
        png_files = list(td_path.glob("page-*.png"))
        if not png_files:
            return False

        pw, ph = page_size_pts
        img = Image.open(png_files[0])
        iw, ih = img.size
        sx = iw / pw
        sy = ih / ph
        x0, y0, x1, y1 = bbox_pts
        crop_box = (
            max(0, int(x0 * sx)),
            max(0, int(y0 * sy)),
            min(iw, int(x1 * sx)),
            min(ih, int(y1 * sy)),
        )
        cropped = img.crop(crop_box)
        cropped.save(output_path)
    return True
