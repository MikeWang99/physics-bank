#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
PUB = ROOT / "skills" / "physics-bank-web-publisher" / "scripts"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, PUB / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


COMPILE = load("web_publish_compile", "compile_publish_bundle.py")
VALIDATE = load("web_publish_validate", "validate_publish_bundle.py")
SQL = load("web_publish_sql", "build_transaction_sql.py")


def config(allow_degraded=False):
    return {
        "schema": "pocket-cosmos-publish-config/v1",
        "practice_set": {
            "id": "fma-demo",
            "system": "competition",
            "category": "mechanics",
            "practice_kind": "mcq",
            "chapter": 1,
            "chapter_title": "Mechanics",
            "label": "F=ma Demo",
            "title": "F=ma Demo Bank",
            "eyebrow": "F=ma",
            "description": "Demo",
            "sources": [],
        },
        "rendering": {
            "allow_layout_degradation": allow_degraded,
            "choice_layout": "stacked",
        },
        "storage": {"bucket": "question-assets", "prefix": "banks"},
        "answers": {
            "missing_mcq_nudge": "Select an option to record your response."
        },
    }


def classification():
    return {
        "schema": "physics-question-classification/v1",
        "status": "reviewed",
        "curriculum": {
            "course_id": "fma",
            "unit_id": "dynamics",
            "topic_id": "newtons-laws",
            "subtopic_ids": ["friction"],
        },
        "physics_domain": "mechanics",
        "primary_topic": {"name": "Newton's second law", "evidence": "Net force determines acceleration."},
        "secondary_topics": [],
        "knowledge_points": [{"name": "Net force determines acceleration", "role": "required", "evidence": "Required by the question."}],
        "solution_models": [{"name": "Newton's second law", "kind": "governing_law", "role": "primary", "evidence": "Bridges force to acceleration."}],
        "skills": [{"id": "model_selection", "evidence": "Select the force model."}],
        "difficulty": {"level": 3, "drivers": ["requires model selection"]},
        "confidence": 0.95,
        "review": {"reviewed": True, "method": "model-semantic-analysis"},
        "derived_fields_version": "1.0",
    }


def make_bank(root: Path, interleaved=False, with_choice_image=True):
    (root / "assets" / "figures").mkdir(parents=True)
    (root / "assets" / "choices" / "q1").mkdir(parents=True)
    (root / "assets" / "figures" / "fig.png").write_bytes(b"figure-bytes")
    (root / "assets" / "choices" / "q1" / "A-01.png").write_bytes(b"choice-a-bytes")

    if interleaved:
        blocks = [
            {"type": "text", "text": "Shared context. Main stem."},
            {"type": "figure", "asset_id": "fig1", "source_anchor": {"relation": "after", "text": "Main stem."}},
            {"type": "text", "text": "Later text."},
        ]
        stem = "Main stem."
        context = "Shared context."
        # Upstream physics-bank would normally require text coverage; the publisher
        # test focuses specifically on current web-render compatibility.
    else:
        blocks = [
            {"type": "text", "text": "Shared context. Main stem."},
            {"type": "figure", "asset_id": "fig1", "source_anchor": {"relation": "question_end"}},
        ]
        stem = "Main stem."
        context = "Shared context."

    asset_ids = ["fig1"] + (["choice-a"] if with_choice_image else [])
    choices = [{"label": "A", "text": "Option A"}, {"label": "B", "text": "Option B"}]
    q = {
        "id": "q1",
        "context": context,
        "stem": stem,
        "choices": choices,
        "year": 2024,
        "source_pages": [1],
        "source": {"file": "paper.pdf", "original_number": "17"},
        "asset_ids": asset_ids,
        "layout_blocks": blocks,
        "layout_review": {"reviewed": True, "method": "source-page-visual"},
        "classification": classification(),
        "course": "F=ma",
        "unit": "Dynamics",
        "topic": "Newton's Laws",
        "subtopics": ["Friction"],
        "knowledge_points": ["Net force determines acceleration"],
        "solution_models": ["Newton's second law"],
        "skills": ["model_selection"],
        "difficulty": 3,
        "tags": ["course:fma", "unit:dynamics", "topic:newtons-laws", "subtopic:friction", "year:2024"],
        "answer": {"label": "A", "text": None, "evidence": "official-key"},
        "extraction": {"text_reviewed": True},
    }
    (root / "questions.json").write_text(json.dumps({"schema_version": "2.0", "questions": [q]}), encoding="utf-8")
    assets = [{
        "id": "fig1",
        "file": "assets/figures/fig.png",
        "role": "stem",
        "owners": ["q1"],
        "source": {"file": "paper.pdf", "page": 1, "bbox": [1, 2, 100, 80]},
        "reviewed": True,
    }]
    if with_choice_image:
        assets.append({
            "id": "choice-a",
            "file": "assets/choices/q1/A-01.png",
            "role": "choice",
            "choice_label": "A",
            "choice_index": 1,
            "owners": ["q1"],
            "source": {"file": "paper.pdf", "page": 1},
            "reviewed": True,
        })
    (root / "assets.json").write_text(json.dumps({"schema_version": "2.0", "assets": assets}), encoding="utf-8")
    (root / "classification-taxonomy.json").write_text(json.dumps({
        "schema": "physics-bank-curriculum-taxonomy/v1",
        "course": {"id": "fma", "name": "F=ma", "basis": "competition-bank-taxonomy"},
        "units": [],
    }), encoding="utf-8")


class WebPublisherTests(unittest.TestCase):
    def test_compile_maps_current_runtime_and_preserves_bank_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_bank(root)
            bundle = COMPILE.compile_bank(root, config())
            self.assertEqual(bundle["practiceSet"]["id"], "fma-demo")
            item = bundle["questions"][0]
            self.assertEqual(item["question"]["id"], "fma-demo::q1")
            self.assertEqual(item["question"]["position"], 0)
            step = item["version"]["metadata"]["practiceStep"]
            self.assertEqual(step["prompt"], "Shared context.\n\nMain stem.")
            self.assertEqual(step["correctAnswer"], "A")
            self.assertEqual(step["difficulty"], 3)
            self.assertEqual(step["title"], "Question 1")
            self.assertEqual(item["version"]["metadata"]["physicsBank"]["classification"]["physics_domain"], "mechanics")
            self.assertEqual(item["renderCompatibility"]["status"], "native")
            roles = [(a["role"], a["metadata"]["slot"], a.get("choiceKey")) for a in item["assets"]]
            self.assertIn(("stem", "image", None), roles)
            self.assertIn(("choice", "choices.image", "A"), roles)
            self.assertEqual(VALIDATE.validate(bundle, root), [])

    def test_storage_path_is_content_addressed_and_hash_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_bank(root)
            one = COMPILE.compile_bank(root, config())
            two = COMPILE.compile_bank(root, config())
            a = one["questions"][0]["assets"][0]
            self.assertIn(a["sha256"][:12], a["storagePath"])
            self.assertTrue(a["storagePath"].startswith("banks/fma-demo/assets/"))
            self.assertEqual(one["questions"][0]["version"]["contentHash"], two["questions"][0]["version"]["contentHash"])

    def test_interleaved_layout_is_blocked_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_bank(root, interleaved=True, with_choice_image=False)
            with self.assertRaisesRegex(ValueError, "web layout would be degraded"):
                COMPILE.compile_bank(root, config(False))

    def test_interleaved_layout_can_only_be_explicitly_degraded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_bank(root, interleaved=True, with_choice_image=False)
            bundle = COMPILE.compile_bank(root, config(True))
            compat = bundle["questions"][0]["renderCompatibility"]
            self.assertEqual(compat["status"], "degraded")
            pb = bundle["questions"][0]["version"]["metadata"]["physicsBank"]
            self.assertEqual(pb["renderCompatibility"]["status"], "degraded")
            self.assertTrue(pb["layoutBlocks"])

    def test_tampered_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_bank(root)
            bundle = COMPILE.compile_bank(root, config())
            (root / "assets" / "figures" / "fig.png").write_bytes(b"changed")
            errors = VALIDATE.validate(bundle, root)
            self.assertTrue(any("asset SHA mismatch" in e for e in errors))

    def test_sql_is_additive_versioned_and_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_bank(root)
            bundle = COMPILE.compile_bank(root, config())
            sql = SQL.build_sql(bundle)
            self.assertIn("BEGIN;", sql)
            self.assertIn("COMMIT;", sql)
            self.assertIn("WHERE NOT EXISTS", sql)
            self.assertIn("MAX(version) + 1", sql)
            self.assertIn("ON CONFLICT (question_version_id, role, storage_bucket, storage_path) DO NOTHING", sql)
            self.assertNotIn("DELETE FROM public.question_versions", sql)
            self.assertNotIn("UPDATE public.question_versions", sql)


if __name__ == "__main__":
    unittest.main()
