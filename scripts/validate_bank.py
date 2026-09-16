#!/usr/bin/env python3
"""Validate a physics-bank v2 bundle before publishing or downstream export."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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
    referenced_asset_ids: set[str] = set()
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
        answer = q.get("answer")
        if not isinstance(answer, dict):
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
        labels = [str(c.get("label")) for c in choices if isinstance(c, dict) and c.get("label")]
        if labels and len(set(labels)) != len(labels):
            errors.append(f"{qid}: duplicate choice labels")
        question_choice_labels[qid] = set(labels)
        for asset_id in q.get("asset_ids") or []:
            asset_id = str(asset_id)
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
            owners = asset.get("owners") or []
            if owners and qid not in owners:
                errors.append(f"{asset_id}: owners does not include {qid}")
            role = asset.get("role")
            if role not in {"stem", "choice", "shared"}:
                errors.append(f"{asset_id}: invalid asset role {role!r}")
            if role == "choice":
                choice_label = str(asset.get("choice_label") or "")
                if not choice_label:
                    errors.append(f"{asset_id}: choice asset missing choice_label")
                elif labels and choice_label not in set(labels):
                    errors.append(f"{asset_id}: choice_label {choice_label!r} does not match a choice in {qid}")

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
        if role == "choice":
            label = str(asset.get("choice_label") or "")
            if not label:
                errors.append(f"{aid}: choice asset missing choice_label")
            for owner in owners:
                labels = question_choice_labels.get(owner, set())
                if labels and label not in labels:
                    errors.append(f"{aid}: choice_label {label!r} does not match owner {owner}")
        if aid not in referenced_asset_ids and owners:
            warnings.append(f"{aid}: asset has owners but no question references its id")

    report = {"status": "ok" if not errors else "error", "errors": errors, "warnings": warnings, "question_count": len(questions), "asset_count": len(assets)}
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
