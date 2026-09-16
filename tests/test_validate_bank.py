#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("validate_bank", ROOT / "scripts" / "validate_bank.py")
MOD = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)

class ValidateTests(unittest.TestCase):
    def test_requires_review_is_hard_failure_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "questions.json"
            p.write_text(json.dumps({"questions": [{
                "id": "q1", "stem": "Text", "source_pages": [1],
                "requires_manual_review": True, "review_reasons": ["scan"],
                "extraction": {"text_reviewed": False}, "asset_ids": []
            }]}))
            report = MOD.validate(p, None, strict=True, require_text_review=True)
            self.assertEqual(report["status"], "error")
            self.assertGreaterEqual(len(report["errors"]), 2)

    def test_reviewed_question_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "questions.json"
            p.write_text(json.dumps({"questions": [{
                "id": "q1", "stem": "Text", "source_pages": [1],
                "requires_manual_review": False,
                "extraction": {"text_reviewed": True}, "asset_ids": []
            }]}))
            report = MOD.validate(p, None, strict=True, require_text_review=True)
            self.assertEqual(report["status"], "ok")

    def test_missing_asset_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "questions.json"
            a = root / "assets.json"
            p.write_text(json.dumps({"questions": [{
                "id": "q1", "stem": "Text", "source_pages": [1],
                "requires_manual_review": False, "extraction": {"text_reviewed": True},
                "asset_ids": ["fig1"]
            }]}))
            a.write_text(json.dumps({"assets": [{"id":"fig1","file":"assets/figures/missing.png","role":"stem","owners":["q1"],"reviewed":True}]}))
            report = MOD.validate(p, a, strict=True, require_text_review=True)
            self.assertEqual(report["status"], "error")
            self.assertTrue(any("asset file not found" in e for e in report["errors"]))

if __name__ == "__main__":
    unittest.main()
