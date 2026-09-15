#!/usr/bin/env python3
"""Render exam-PDF pages and propose raster/vector graphic candidates.

This deliberately does not require Figure/Fig. captions. Candidate ownership is
left to question-region and visual review; the output is a review queue, not a
final figure manifest.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz


def clusters(rects: list[fitz.Rect], gap_x: float = 18, gap_y: float = 18) -> list[fitz.Rect]:
    """Join nearby raster/vector drawing rectangles using a small page-space gap."""
    parent = list(range(len(rects)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def join(a: int, b: int) -> None:
        a, b = root(a), root(b)
        if a != b:
            parent[b] = a

    def nearby(a: fitz.Rect, b: fitz.Rect) -> bool:
        return not (a.x1 + gap_x < b.x0 or b.x1 + gap_x < a.x0 or
                    a.y1 + gap_y < b.y0 or b.y1 + gap_y < a.y0)

    for i, rect in enumerate(rects):
        for j in range(i):
            if nearby(rect, rects[j]):
                join(i, j)
    grouped: dict[int, fitz.Rect] = {}
    for i, rect in enumerate(rects):
        r = root(i)
        if r not in grouped:
            grouped[r] = fitz.Rect(rect)
        else:
            grouped[r].include_rect(rect)
    return list(grouped.values())


def graphics_on_page(page: fitz.Page) -> list[fitz.Rect]:
    """Return non-trivial raster placements and vector-drawing bounds.

    Ignore tiny marks and page-sized backgrounds. Text labels are intentionally
    not included here; the review pass expands a candidate box when needed.
    """
    rects: list[fitz.Rect] = []
    page_area = page.rect.width * page.rect.height
    for image in page.get_images(full=True):
        try:
            for rect in page.get_image_rects(image[0]):
                if rect.width >= 8 and rect.height >= 8:
                    rects.append(fitz.Rect(rect))
        except Exception:
            pass
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue
        rect = fitz.Rect(rect)
        if rect.width < 6 or rect.height < 6 or rect.width * rect.height > page_area * 0.40:
            continue
        fill = drawing.get("fill")
        white_fill = fill is not None and len(fill) >= 3 and all(c >= .92 for c in fill[:3])
        if white_fill and rect.width * rect.height > page_area * .15:
            continue
        rects.append(rect)
    return rects


QUESTION_RE = re.compile(r"^\s*(\d{1,3})\s*[.)]")


def question_hints(page: fitz.Page) -> list[dict]:
    hints = []
    # A PDF text block can contain several question paragraphs. Inspect lines so
    # a question beginning in the middle of a block is not silently skipped.
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", []))
            match = QUESTION_RE.match(text)
            if match:
                hints.append({"number": match.group(1), "y": round(line["bbox"][1], 2)})
    # Some PDFs duplicate a line in overlapping text blocks; retain one hint per
    # question number/vertical coordinate while preserving document order.
    unique = {(item["number"], item["y"]): item for item in hints}
    return sorted(unique.values(), key=lambda item: item["y"])


def owner_hint(rect: fitz.Rect, questions: list[dict]) -> str | None:
    preceding = [q for q in questions if q["y"] <= rect.y0 + 2]
    return preceding[-1]["number"] if preceding else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--zoom", type=float, default=6.0)
    parser.add_argument("--pages", help="1-based pages, e.g. 2,4-6; defaults to all")
    parser.add_argument("--padding", type=float, default=18.0, help="candidate padding in PDF points")
    args = parser.parse_args()
    if not args.pdf.is_file() or args.pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"Not a readable PDF: {args.pdf}")

    selected: set[int] | None = None
    if args.pages:
        selected = set()
        for part in args.pages.split(","):
            lo, _, hi = part.strip().partition("-")
            start, end = int(lo), int(hi or lo)
            selected.update(range(start, end + 1))

    pages_dir = args.outdir / "pages"
    candidate_dir = args.outdir / "candidates"
    pages_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(args.pdf)
    scale = fitz.Matrix(args.zoom, args.zoom)
    manifest = {"source_pdf": str(args.pdf), "zoom": args.zoom, "candidates": []}

    for index, page in enumerate(doc, start=1):
        if selected is not None and index not in selected:
            continue
        page_png = pages_dir / f"page-{index:03d}.png"
        page.get_pixmap(matrix=scale, alpha=False).save(page_png)
        hints = question_hints(page)
        for number, rect in enumerate(clusters(graphics_on_page(page)), start=1):
            clip = fitz.Rect(rect.x0 - args.padding, rect.y0 - args.padding,
                             rect.x1 + args.padding, rect.y1 + args.padding) & page.rect
            if clip.width < 12 or clip.height < 12:
                continue
            filename = f"page-{index:03d}-candidate-{number:02d}.png"
            output = candidate_dir / filename
            page.get_pixmap(matrix=scale, clip=clip, alpha=False).save(output)
            manifest["candidates"].append({
                "id": f"p{index:03d}-c{number:02d}",
                "file": f"candidates/{filename}",
                "page": index,
                # This is deliberately only geometric context. A shared setup
                # graphic can sit before the first question that uses it.
                "nearest_question_above_hint": owner_hint(clip, hints),
                "bbox_pdf_points": [round(v, 2) for v in (clip.x0, clip.y0, clip.x1, clip.y1)],
                "status": "unreviewed"
            })
    (args.outdir / "candidates.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Rendered {len(list(pages_dir.glob('*.png')))} page(s) and proposed {len(manifest['candidates'])} candidate(s): {args.outdir}")


if __name__ == "__main__":
    main()
