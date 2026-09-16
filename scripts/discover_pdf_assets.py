#!/usr/bin/env python3
"""Render exam PDF pages and propose non-page-sized raster/vector figure candidates."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import fitz

QUESTION_PATTERNS = [
    re.compile(r"^\s*(?:Question\s+|Q\s*)?(\d{1,3})\s*[.)][:.-]?", re.I),
    re.compile(r"^\s*(?:Question\s+|Q\s*)(\d{1,3})\b", re.I),
    re.compile(r"^\s*(\d{1,3})\s*$"),
]


def clusters(rects: list[fitz.Rect], gap_x: float = 18, gap_y: float = 18) -> list[fitz.Rect]:
    parent=list(range(len(rects)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]; i=parent[i]
        return i
    def join(a,b):
        a,b=root(a),root(b)
        if a!=b: parent[b]=a
    def nearby(a,b):
        return not (a.x1+gap_x<b.x0 or b.x1+gap_x<a.x0 or a.y1+gap_y<b.y0 or b.y1+gap_y<a.y0)
    for i,r in enumerate(rects):
        for j in range(i):
            if nearby(r,rects[j]): join(i,j)
    grouped={}
    for i,r in enumerate(rects):
        k=root(i)
        if k not in grouped: grouped[k]=fitz.Rect(r)
        else: grouped[k].include_rect(r)
    return list(grouped.values())


def graphics_on_page(page: fitz.Page) -> tuple[list[fitz.Rect], bool]:
    """Return candidate graphics and whether a page-sized scan/raster was detected."""
    rects=[]; page_area=page.rect.width*page.rect.height; full_page_raster=False
    for image in page.get_images(full=True):
        try:
            for rect in page.get_image_rects(image[0]):
                area=rect.width*rect.height
                if area > page_area*0.70:
                    full_page_raster=True
                    continue
                if rect.width>=8 and rect.height>=8: rects.append(fitz.Rect(rect))
        except Exception:
            pass
    for drawing in page.get_drawings():
        rect=drawing.get("rect")
        if rect is None: continue
        rect=fitz.Rect(rect); area=rect.width*rect.height
        if rect.width<6 or rect.height<6 or area>page_area*0.40: continue
        fill=drawing.get("fill")
        white_fill=fill is not None and len(fill)>=3 and all(c>=.92 for c in fill[:3])
        if white_fill and area>page_area*.15: continue
        rects.append(rect)
    return rects, full_page_raster


def anchor_number(text: str):
    for pattern in QUESTION_PATTERNS:
        m=pattern.match(text)
        if m: return m.group(1)
    return None


def question_hints(page: fitz.Page) -> list[dict]:
    hints=[]
    for block in page.get_text("dict").get("blocks",[]):
        if block.get("type")!=0: continue
        for line in block.get("lines",[]):
            text="".join(span.get("text","") for span in line.get("spans",[])).strip()
            num=anchor_number(text)
            if num: hints.append({"number":num,"y":round(line["bbox"][1],2)})
    unique={(x["number"],x["y"]):x for x in hints}
    return sorted(unique.values(), key=lambda x:x["y"])


def owner_hint(rect, questions):
    preceding=[q for q in questions if q["y"]<=rect.y0+2]
    return preceding[-1]["number"] if preceding else None


def parse_pages(value: str|None):
    if not value: return None
    selected=set()
    for part in value.split(","):
        lo,_,hi=part.strip().partition("-"); start,end=int(lo),int(hi or lo)
        selected.update(range(start,end+1))
    return selected


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("pdf",type=Path); ap.add_argument("--outdir",required=True,type=Path)
    ap.add_argument("--zoom",type=float,default=6.0); ap.add_argument("--pages"); ap.add_argument("--padding",type=float,default=18.0)
    args=ap.parse_args()
    if not args.pdf.is_file() or args.pdf.suffix.lower()!=".pdf": raise SystemExit(f"Not a readable PDF: {args.pdf}")
    selected=parse_pages(args.pages); pages_dir=args.outdir/"pages"; cand_dir=args.outdir/"candidates"; pages_dir.mkdir(parents=True,exist_ok=True); cand_dir.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(args.pdf); scale=fitz.Matrix(args.zoom,args.zoom)
    manifest={"schema_version":"2.0","source_pdf":str(args.pdf),"zoom":args.zoom,"pages":[],"candidates":[]}
    for index,page in enumerate(doc,start=1):
        if selected is not None and index not in selected: continue
        page_png=pages_dir/f"page-{index:03d}.png"; page.get_pixmap(matrix=scale,alpha=False).save(page_png)
        rects,full_page_raster=graphics_on_page(page); hints=question_hints(page)
        manifest["pages"].append({"page":index,"render":f"pages/{page_png.name}","full_page_raster_detected":full_page_raster,"question_hints":hints})
        for number,rect in enumerate(clusters(rects),start=1):
            clip=fitz.Rect(rect.x0-args.padding,rect.y0-args.padding,rect.x1+args.padding,rect.y1+args.padding)&page.rect
            if clip.width<12 or clip.height<12: continue
            filename=f"page-{index:03d}-candidate-{number:02d}.png"; output=cand_dir/filename; page.get_pixmap(matrix=scale,clip=clip,alpha=False).save(output)
            manifest["candidates"].append({"id":f"p{index:03d}-c{number:02d}","file":f"candidates/{filename}","page":index,"nearest_question_above_hint":owner_hint(clip,hints),"bbox_pdf_points":[round(v,2) for v in (clip.x0,clip.y0,clip.x1,clip.y1)],"status":"unreviewed"})
    (args.outdir/"candidates.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(f"Rendered {len(manifest['pages'])} page(s) and proposed {len(manifest['candidates'])} candidate(s): {args.outdir}")

if __name__=="__main__": main()
