"""Layout detection: find figures, tables, and captions on a PDF page.

The core observation behind figgydeck: in Elsevier-style textbooks, content
is reliably distinguishable by font size:

    - 10 pt   body / running text
    - 9 pt    "FIGURE X.Y" and "TABLE X.Y" labels (bold)
    - 8 pt    caption body text

Combined with column-aware spatial matching (a label sits immediately below
the figure it describes), this is enough to extract clean figure/caption
pairs without any LLM call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------- Tunables (Elsevier laboratory-animal series defaults) ----------

LABEL_SIZE = 9.0      # "FIGURE X.Y" / "TABLE X.Y"
CAPTION_SIZE = 8.0    # caption body text
SIZE_TOL = 0.3        # how close to the target a font size must be (pt)


@dataclass
class Label:
    """A FIGURE or TABLE label found on the page."""
    kind: str                 # "figure" | "table"
    number: str               # e.g. "1.4"
    inline_title: str = ""    # only set for tables; figures have no inline title
    x: float = 0.0
    y: float = 0.0
    column: int = 0           # 0 = left, 1 = right


@dataclass
class ImageBox:
    """A bitmap image embedded on the page, with bounding box."""
    page_index: int
    x0: float
    y0: float
    x1: float
    y1: float
    columns: set[int] = field(default_factory=set)


@dataclass
class HRule:
    """A horizontal rule (line) detected on the page."""
    x0: float
    x1: float
    y: float


@dataclass
class PageEntry:
    """One figure or table found on a page, ready for downstream consumption."""
    number: str
    type: str                 # "figure" | "table"
    page: int
    caption_raw: str
    inline_title: str
    label_xy: tuple[float, float]
    matched_image_idx_on_page: int | None
    matched_image_bbox: tuple[float, float, float, float] | None
    table_bbox: tuple[float, float, float, float] | None
    page_size: tuple[float, float]


# ---------- Geometry helpers ----------

def column_of(x: float, page_width: float) -> int:
    """0 = left column, 1 = right column."""
    return 0 if x < page_width / 2 else 1


def image_columns(img, page_width: float) -> set[int]:
    """Set of columns the image occupies. Wide images that cross the midline
    return {0, 1} so they can match labels in either column."""
    return {column_of(img["x0"], page_width), column_of(img["x1"], page_width)}


# ---------- Char grouping ----------

def group_chars_into_lines(chars):
    """Group consecutive chars on the same baseline into line strings.

    Uses a generous gap threshold (matches the printed space between
    "FIGURE" and "1.4") and inserts spaces at obvious word boundaries.

    Returns list of (text, x0, top) tuples.
    """
    chars = sorted(chars, key=lambda c: (round(c["top"], 0), c["x0"]))
    lines: list[tuple[str, float, float]] = []
    cur: list = []

    def flush(group):
        if not group:
            return
        out = [group[0]["text"]]
        for prev, c in zip(group, group[1:], strict=False):
            gap = c["x0"] - prev["x1"]
            if gap > 1.5:
                out.append(" ")
            out.append(c["text"])
        text = "".join(out)
        lines.append((text, group[0]["x0"], group[0]["top"]))

    for c in chars:
        if not cur:
            cur = [c]
        elif (
            abs(c["top"] - cur[-1]["top"]) < 2
            and c["x0"] - cur[-1]["x1"] < 12
        ):
            cur.append(c)
        else:
            flush(cur)
            cur = [c]
    flush(cur)
    return lines


# ---------- Label parsing ----------

LABEL_RE = re.compile(r"^(FIGURE|TABLE)\s*([\d.]+[A-Za-z]?)(.*)$")


def parse_labels(raw_lines, page_width: float) -> list[Label]:
    """Find labels in the raw line list and attach wrapped continuation
    lines (for table titles that wrap to a second line)."""
    labels: list[Label] = []
    for text, x, y in raw_lines:
        m = LABEL_RE.match(text.strip())
        if m:
            labels.append(Label(
                kind=m.group(1).lower(),
                number=m.group(2).rstrip("."),
                inline_title=m.group(3).strip(" ."),
                x=x, y=y,
                column=column_of(x, page_width),
            ))

    # Attach wrapped continuation text to the most recent TABLE label above
    # it in the same column.
    for raw_text, raw_x, raw_y in raw_lines:
        if LABEL_RE.match(raw_text.strip()):
            continue
        for lbl in labels:
            if lbl.kind != "table":
                continue
            dy = raw_y - lbl.y
            if 0 < dy < 25 and column_of(raw_x, page_width) == lbl.column:
                extra = raw_text.strip(" .")
                if extra:
                    sep = " " if lbl.inline_title else ""
                    lbl.inline_title = lbl.inline_title + sep + extra
                break

    return labels


# ---------- Horizontal rule detection ----------

def find_h_rules(page) -> list[HRule]:
    """Find horizontal rules used as table borders.

    Excludes the running-header rule near the top of the page and any
    spurious thin marks at the very bottom. Rules of the same y-position
    rendered as multiple edges (1pt rules can show as 2 edges) are deduped.
    """
    rules = []
    for e in page.edges:
        if e["orientation"] != "h":
            continue
        if e["top"] < 40 or e["top"] > page.height - 40:
            continue
        if e["width"] < 60:
            continue
        rules.append(HRule(x0=e["x0"], x1=e["x1"], y=e["top"]))

    rules.sort(key=lambda r: r.y)
    deduped: list[HRule] = []
    for r in rules:
        if deduped and abs(r.y - deduped[-1].y) < 2 and abs(r.x0 - deduped[-1].x0) < 2:
            continue
        deduped.append(r)
    return deduped


# ---------- Caption extraction ----------

def reconstruct_text_from_chars(chars, line_gap: float = 3.0, word_gap: float = 1.5) -> str:
    """Sort chars by (line, x) and stitch back into text with newlines/spaces."""
    if not chars:
        return ""
    chars = sorted(chars, key=lambda c: (round(c["top"], 0), c["x0"]))
    out = []
    last_top = None
    last_x1 = None
    for c in chars:
        if last_top is None:
            out.append(c["text"])
        else:
            dy = c["top"] - last_top
            dx = c["x0"] - last_x1
            if dy > line_gap:
                out.append("\n")
                out.append(c["text"])
            elif dx > word_gap:
                out.append(" " + c["text"])
            else:
                out.append(c["text"])
        last_top = c["top"]
        last_x1 = c["x1"]
    return "".join(out)


# ---------- Per-page extraction ----------

def extract_page(page, page_num: int) -> list[PageEntry]:
    """Extract figures and tables from a single page."""
    width = page.width

    # 1. Find labels
    label_chars = [c for c in page.chars if abs(c["size"] - LABEL_SIZE) < SIZE_TOL]
    raw_lines = group_chars_into_lines(label_chars)
    labels = parse_labels(raw_lines, width)

    # 2. Find images
    images: list[ImageBox] = []
    for idx, img in enumerate(page.images):
        images.append(ImageBox(
            page_index=idx,
            x0=img["x0"], y0=img["top"],
            x1=img["x1"], y1=img["bottom"],
            columns=image_columns(img, width),
        ))

    # 3. Find horizontal rules (for table boundaries)
    h_rules = find_h_rules(page)

    # 4. Get caption-sized text
    caption_chars = [c for c in page.chars if abs(c["size"] - CAPTION_SIZE) < SIZE_TOL]

    # 5. For each label, compute caption text + matched image / table bbox
    results: list[PageEntry] = []
    labels_sorted = sorted(labels, key=lambda lb: (lb.column, lb.y))

    for i, lbl in enumerate(labels_sorted):
        # Caption boundary = next label/image start (same column) or page end
        next_y = page.height
        for other in labels_sorted[i + 1:]:
            if other.column == lbl.column and other.y > lbl.y:
                next_y = other.y
                break
        for img in images:
            if lbl.column in img.columns and img.y0 > lbl.y:
                next_y = min(next_y, img.y0)
                break

        col_caption_chars = [
            c for c in caption_chars
            if column_of((c["x0"] + c["x1"]) / 2, width) == lbl.column
            and c["top"] >= lbl.y - 2
            and c["top"] < next_y - 2
        ]
        cap_text = reconstruct_text_from_chars(col_caption_chars)

        matched_image: ImageBox | None = None
        table_bbox: tuple[float, float, float, float] | None = None

        if lbl.kind == "figure":
            # Image is just above the label, in the same column
            candidates = [
                img for img in images
                if lbl.column in img.columns and img.y1 <= lbl.y + 2
            ]
            if candidates:
                matched_image = max(candidates, key=lambda im: im.y1)

        elif lbl.kind == "table":
            # Find horizontal rules that bracket the table.
            mid = width / 2

            def rule_overlaps_label_col(r, _lbl_col=lbl.column, _mid=mid):
                if _lbl_col == 0:
                    return r.x0 < _mid
                return r.x1 > _mid

            below = [r for r in h_rules if rule_overlaps_label_col(r) and r.y > lbl.y]
            bracketing = [r for r in below if r.y < next_y + 2]
            if bracketing:
                bot_y = bracketing[-1].y
                widest = max(bracketing, key=lambda r: r.x1 - r.x0)
                table_bbox = (
                    widest.x0 - 4,
                    lbl.y - 4,
                    widest.x1 + 4,
                    bot_y + 24,  # extra room for source line ("From Heston et al....")
                )

        results.append(PageEntry(
            number=lbl.number,
            type=lbl.kind,
            page=page_num,
            caption_raw=cap_text,
            inline_title=lbl.inline_title,
            label_xy=(lbl.x, lbl.y),
            matched_image_idx_on_page=matched_image.page_index if matched_image else None,
            matched_image_bbox=(
                (matched_image.x0, matched_image.y0,
                 matched_image.x1, matched_image.y1)
                if matched_image else None
            ),
            table_bbox=table_bbox,
            page_size=(page.width, page.height),
        ))

    return results
