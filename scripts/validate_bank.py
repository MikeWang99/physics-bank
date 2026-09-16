#!/usr/bin/env python3
"""Validate a physics-bank v2 bundle before publishing or downstream export."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _label(value) -> str:
    return str(value or "").strip().upper()


def validate(questions_path: Path, assets_path: Path | None, strict: bool, require_text_review: bool) -> dict:
    root = questions_path.parent
    data = load_json(questions_path)
    questions = data.get("questions")
    if not isinstance(questions, list):
        raise ValueError("questions.json must contain a top-level questions array")
    asset_data = load_json(assets_path) if assets_path and assets_path.exists() else {"assets": data.get("assets", [])}
    assets = asset_data.get("assets", [])
    asset_ids = [str(a.get("id")) for a in assets if a.get("id")]
    asset_index = {str(a.get("id")): a for a in assets if a.get("id")}

    errors: list[str] = []
    warnings: list[str] = []
    if len(asset_ids) != len(set(asset_ids)):
        errors.append("duplicate asset ids")

    seen: set[str] = set()
    question_choice_labels: dict[str, set[str]] = {}
    question_choice_entries: dict[str, dict[str, dict]] = {}
    referenced_asset_ids: set[str] = set()
    choice_pairs: dict[tuple[str, str, int], str] = {}
    choice_files: dict[str, str] = {}

    for q in questions:
        qid = str(q.get("id") or "")
        if not qid:
            errors.append("question missing id")
            continue
        if qid in seen:
            errors.append(f"duplicate question id: {qid}")
        seen.add(qid)
        if strict and q.get("content_format") != "markdown+latex":
            errors.append(f"{qid}: content_format must be markdown+latex")
        if not isinstance(q.get("answer"), dict):
            errors.append(f"{qid}: answer object is required")
        stem = str(q.get("stem") or q.get("stem_markdown") or "").strip()
        context = str(q.get("context") or "").strip()
        if not stem and not context:
            errors.append(f"{qid}: empty stem/context")
        pages = q.get("source_pages") or []
        if not pages:
            source = q.get("source") or {}
            if source.get("page"):
                pages = [source["page"]]
            else:
                errors.append(f"{qid}: missing source_pages/source.page")
        extraction = q.get("extraction") or {}
        if require_text_review and not extraction.get("text_reviewed"):
            errors.append(f"{qid}: extraction.text_reviewed is not true")
        if q.get("requires_manual_review"):
            msg = f"{qid}: requires_manual_review ({', '.join(q.get('review_reasons') or [])})"
            (errors if strict else warnings).append(msg)

        choices = q.get("choices") or []
        labels = [_label(c.get("label")) for c in choices if isinstance(c, dict) and c.get("label")]
        if labels and len(set(labels)) != len(labels):
            errors.append(f"{qid}: duplicate choice labels")
        question_choice_labels[qid] = set(labels)
        question_choice_entries[qid] = {
            _label(c.get("label")): c for c in choices if isinstance(c, dict) and c.get("label")
        }

        top_ids = [str(v) for v in (q.get("asset_ids") or [])]
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            label = _label(choice.get("label"))
            for aid in [str(v) for v in (choice.get("asset_ids") or [])]:
                asset = asset_index.get(aid)
                if asset is None:
                    errors.append(f"{qid} choice {label}: missing asset record {aid}")
                    continue
                if asset.get("role") != "choice":
                    errors.append(f"{qid} choice {label}: {aid} is not a choice asset")
                if _label(asset.get("choice_label")) != label:
                    errors.append(f"{qid} choice {label}: {aid} has mismatched choice_label")
                if qid not in [str(v) for v in (asset.get("owners") or [])]:
                    errors.append(f"{qid} choice {label}: {aid} does not belong to this question")
                if aid not in top_ids:
                    errors.append(f"{qid} choice {label}: {aid} must also appear in question.asset_ids")

        for asset_id in top_ids:
            referenced_asset_ids.add(asset_id)
            asset = asset_index.get(asset_id)
            if asset is None:
                errors.append(f"{qid}: missing asset record {asset_id}")
                continue
            file_value = asset.get("file") or asset.get("path")
            if not file_value:
                errors.append(f"{asset_id}: asset has no file/path")
            else:
                asset_path = Path(file_value) if Path(file_value).is_absolute() else root / file_value
                if not asset_path.exists():
                    errors.append(f"{asset_id}: asset file not found: {file_value}")
            if not asset.get("reviewed", asset.get("crop", {}).get("reviewed", False)):
                errors.append(f"{asset_id}: final asset not visually reviewed")
            owners = [str(v) for v in (asset.get("owners") or [])]
            if owners and qid not in owners:
                errors.append(f"{asset_id}: owners does not include {qid}")
            role = asset.get("role")
            if role not in {"stem", "choice", "shared"}:
                errors.append(f"{asset_id}: invalid asset role {role!r}")

            if role == "choice":
                label = _label(asset.get("choice_label"))
                index = asset.get("choice_index", 1)
                if len(owners) != 1:
                    errors.append(f"{asset_id}: choice asset must have exactly one owner")
                if not label:
                    errors.append(f"{asset_id}: choice asset missing choice_label")
                elif labels and label not in set(labels):
                    errors.append(f"{asset_id}: choice_label {label!r} does not match a choice in {qid}")
                if not isinstance(index, int) or index < 1:
                    errors.append(f"{asset_id}: choice_index must be a positive integer")
                crop = asset.get("crop") or {}
                if crop.get("isolated_choice") is not True:
                    errors.append(f"{asset_id}: crop.isolated_choice must be true for final choice assets")
                if file_value and len(owners) == 1 and label and isinstance(index, int) and index > 0:
                    rel = Path(str(file_value))
                    expected_parent = Path("assets") / "choices" / owners[0]
                    expected_stem = f"{label}-{index:02d}"
                    if rel.is_absolute() or rel.parent != expected_parent or rel.stem != expected_stem:
                        errors.append(
                            f"{asset_id}: choice asset must live at assets/choices/{owners[0]}/{expected_stem}.<ext>"
                        )
                    key = (owners[0], label, index)
                    prev = choice_pairs.get(key)
                    if prev and prev != asset_id:
                        errors.append(f"{asset_id}: duplicate choice asset slot {owners[0]} {label}-{index:02d} (also {prev})")
                    choice_pairs[key] = asset_id
                    normalized_file = rel.as_posix()
                    prev_file = choice_files.get(normalized_file)
                    if prev_file and prev_file != asset_id:
                        errors.append(f"{asset_id}: choice asset file is also used by {prev_file}")
                    choice_files[normalized_file] = asset_id
                    entry = question_choice_entries.get(qid, {}).get(label)
                    if entry is not None and asset_id not in [str(v) for v in (entry.get("asset_ids") or [])]:
                        errors.append(f"{asset_id}: matching choice {qid}/{label} must reference it in choices[].asset_ids")

    question_ids = seen
    for asset in assets:
        aid = str(asset.get("id") or "<unnamed asset>")
        owners = [str(v) for v in (asset.get("owners") or asset.get("shared_with") or [])]
        if not owners:
            warnings.append(f"{aid}: orphan asset has no owners")
        for owner in owners:
            if owner not in question_ids:
                errors.append(f"{aid}: unknown owner question {owner}")
        role = asset.get("role")
        if role not in {"stem", "choice", "shared"}:
            errors.append(f"{aid}: invalid asset role {role!r}")
        if aid not in referenced_asset_ids and owners:
            warnings.append(f"{aid}: asset has owners but no question references its id")

    report = {
        "status": "ok" if not errors else "error",
        "errors": errors,
        "warnings": warnings,
        "question_count": len(questions),
        "asset_count": len(assets),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("questions", type=Path)
    parser.add_argument("--assets", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--require-text-review", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate(args.questions, args.assets, args.strict, args.require_text_review)
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")
    for error in report["errors"]:
        print(f"ERROR: {error}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
