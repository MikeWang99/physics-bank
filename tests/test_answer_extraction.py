#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("bank_answer_validation", ROOT/"scripts"/"validate_bank.py")
VAL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VAL)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_question(answer):
    return {
        "id": "q1", "stem": "Find the acceleration.", "context": "",
        "content_format": "markdown+latex", "source_pages": [1],
        "choices": [{"label": "A", "text": "4"}, {"label": "B", "text": "6"}],
        "asset_ids": [], "extraction": {"text_reviewed": True},
        "requires_manual_review": False, "answer": answer
    }


def write_bank(root, q, assets=None):
    qp = root/"questions.json"
    ap = root/"assets.json"
    qp.write_text(json.dumps({"questions": [q]}), encoding="utf-8")
    ap.write_text(json.dumps({"assets": assets or []}), encoding="utf-8")
    return qp, ap


def worked_source(root):
    source = root/"assets"/"source"/"worked.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(220, 220, 320, 280), width=2)
    doc.save(source)
    doc.close()

    bbox = [180, 185, 360, 315]
    dest = root/"assets"/"answers"/"q1"/"diagram-01.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(source)
    doc[1].get_pixmap(matrix=fitz.Matrix(2, 2), clip=fitz.Rect(*bbox), alpha=False).save(dest)
    doc.close()

    asset = {
        "id":"q1-answer-01", "role":"answer", "file":"assets/answers/q1/diagram-01.png",
        "owners":["q1"], "reviewed":True,
        "source":{"file":"assets/source/worked.pdf","page":2,"bbox":bbox},
        "crop":{
            "reviewed":True,"review_sha256":sha(dest),"review_source_sha256":sha(source),
            "reviewed_source_bbox":bbox,"source_neighborhood_reviewed":True,
            "review_method":"source-page-halo+final-file"
        }
    }
    answer = {
        "kind":"worked_solution","label":"A",
        "text":"Draw the forces. $F=ma$.",
        "evidence":"official-explanation",
        "source":{"file":"assets/source/worked.pdf","page":2,"bbox":[150,160,420,340]},
        "extraction":{"reviewed":True,"method":"source-page-visual","raw_source_text":"Draw the forces. F = ma."},
        "asset_ids":["q1-answer-01"],
        "layout_blocks":[
            {"type":"text","text":"Draw the forces."},
            {"type":"figure","asset_id":"q1-answer-01"},
            {"type":"text","text":"$F=ma$."}
        ],
        "layout_review":{"reviewed":True,"method":"source-page-visual"}
    }
    q = base_question(answer)
    q["asset_ids"] = ["q1-answer-01"]
    return q, asset, dest


class AnswerExtractionTests(unittest.TestCase):
    def test_legacy_answer_without_kind_remains_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            q=base_question({"label":"A","text":None,"evidence":"official-key"})
            qp,ap=write_bank(root,q)
            self.assertEqual(VAL.validate(qp,ap,strict=True,require_text_review=True)["status"],"ok")

    def test_key_only_contains_no_invented_solution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); src=root/"assets"/"source"/"answer-key.pdf"
            src.parent.mkdir(parents=True)
            src.write_bytes(b"raw source supplied by user")
            q=base_question({
                "kind":"key_only","label":"A","text":None,
                "evidence":"official-key","source":{"file":"assets/source/answer-key.pdf","page":1}
            })
            qp,ap=write_bank(root,q)
            self.assertEqual(VAL.validate(qp,ap,strict=True,require_text_review=True)["status"],"ok")

    def test_key_only_with_official_attribution_in_solution_rejected(self):
        q=base_question({
            "kind":"key_only","label":"A",
            "text":"According to the AAPT official answer key, the answer is A.",
            "evidence":"official-key"
        })
        issues=VAL.validate_answer_content(q,{},strict=True)
        self.assertTrue(any("key_only" in e for e in issues), issues)

    def test_answer_option_must_match_choices(self):
        q=base_question({"kind":"key_only","label":"Z","text":None,"evidence":"official-key"})
        issues=VAL.validate_answer_content(q,{},strict=True)
        self.assertTrue(any("does not match any choice" in e for e in issues), issues)

    def test_reviewed_worked_answer_figure_passes_strict_and_answer_page_may_differ(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            q,a,_=worked_source(root)
            qp,ap=write_bank(root,q,[a])
            report=VAL.validate(qp,ap,strict=True,require_text_review=True)
            self.assertEqual(report["status"],"ok",report["errors"])

    def test_missing_answer_layout_figure_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            q,a,_=worked_source(root)
            q["answer"]["layout_blocks"]=[{"type":"text","text":"Draw the forces. $F=ma$."}]
            qp,ap=write_bank(root,q,[a])
            errors=VAL.validate(qp,ap,strict=True,require_text_review=True)["errors"]
            self.assertTrue(any("answer figure must occur exactly once" in e for e in errors), errors)

    def test_missing_educational_prose_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            q,a,_=worked_source(root)
            q["answer"]["layout_blocks"]=[
                {"type":"text","text":"Draw the forces."},
                {"type":"figure","asset_id":"q1-answer-01"}
            ]
            qp,ap=write_bank(root,q,[a])
            errors=VAL.validate(qp,ap,strict=True,require_text_review=True)["errors"]
            self.assertTrue(any("answer.layout_blocks text" in e for e in errors),errors)

    def test_answer_figure_change_invalidates_review_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            q,a,img=worked_source(root)
            img.write_bytes(img.read_bytes()+b"tampered")
            qp,ap=write_bank(root,q,[a])
            errors=VAL.validate(qp,ap,strict=True,require_text_review=True)["errors"]
            self.assertTrue(any("changed after visual review" in e for e in errors),errors)

    def test_signature_omission_must_be_documented_and_reviewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            q,a,_=worked_source(root)
            q["answer"]["excluded_non_instructional"]=[
                {"kind":"signature","source_bbox":[410,350,510,370],"reason":"Author name, not a diagram label"}
            ]
            qp,ap=write_bank(root,q,[a])
            self.assertEqual(VAL.validate(qp,ap,strict=True,require_text_review=True)["status"],"ok")
            q["answer"]["excluded_non_instructional"][0]["reason"]=""
            qp,ap=write_bank(root,q,[a])
            errors=VAL.validate(qp,ap,strict=True,require_text_review=True)["errors"]
            self.assertTrue(any("requires reason" in e for e in errors),errors)

    def test_bare_latex_in_answer_layout_is_rejected(self):
        q=base_question({
            "kind":"worked_solution","text":"Use $F=ma$.","label":"A",
            "evidence":"official-explanation",
            "source":{"file":"answers.pdf","page":1},
            "extraction":{"method":"source-page-visual","reviewed":True},
            "layout_blocks":[{"type":"text","text":r"Use \mu_s."}]
        })
        issues=VAL.question_math_issues(q)
        self.assertTrue(any("answer.layout_blocks" in e for e in issues),issues)


if __name__ == "__main__":
    unittest.main()
