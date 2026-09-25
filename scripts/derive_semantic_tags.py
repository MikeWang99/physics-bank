#!/usr/bin/env python3
"""Derive searchable compatibility fields/tags from canonical semantic classification."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

GENERATED_PREFIXES = (
    "course:", "unit:", "topic:", "subtopic:", "domain:",
    "primary-topic:", "secondary-topic:", "model:", "skill:", "difficulty:"
)


def slugify(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"['’]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def taxonomy_index(data: dict) -> dict:
    course = data.get("course") or {}
    units = {}
    topics = {}
    subtopics = {}
    for unit in data.get("units") or []:
        uid = str(unit.get("id") or "")
        units[uid] = unit
        for topic in unit.get("topics") or []:
            tid = str(topic.get("id") or "")
            topics[tid] = (uid, topic)
            for sub in topic.get("subtopics") or []:
                sid = str(sub.get("id") or "")
                subtopics[sid] = (uid, tid, sub)
    return {"course": course, "units": units, "topics": topics, "subtopics": subtopics}


def names_from_classification(classification: dict, taxonomy: dict) -> dict:
    idx = taxonomy_index(taxonomy)
    cur = classification.get("curriculum") or {}
    uid = str(cur.get("unit_id") or "")
    tid = str(cur.get("topic_id") or "")
    sids = [str(v) for v in (cur.get("subtopic_ids") or [])]
    course_name = str(idx["course"].get("name") or "")
    unit_name = str((idx["units"].get(uid) or {}).get("name") or "")
    topic_name = str(((idx["topics"].get(tid) or ("", {}))[1]).get("name") or "")
    sub_names = [
        str((idx["subtopics"].get(sid) or ("", "", {}))[2].get("name") or "")
        for sid in sids
    ]
    return {
        "course": course_name,
        "unit": unit_name,
        "topic": topic_name,
        "subtopics": [v for v in sub_names if v],
    }


def derived_tags(question: dict, taxonomy: dict) -> list[str]:
    c = question.get("classification") or {}
    cur = c.get("curriculum") or {}
    tags = []
    course_id = str(cur.get("course_id") or "")
    unit_id = str(cur.get("unit_id") or "")
    topic_id = str(cur.get("topic_id") or "")
    subtopic_ids = [str(v) for v in (cur.get("subtopic_ids") or [])]
    if course_id:
        tags.append(f"course:{course_id}")
    if unit_id:
        tags.append(f"unit:{unit_id}")
    if topic_id:
        tags.append(f"topic:{topic_id}")
    tags.extend(f"subtopic:{sid}" for sid in subtopic_ids if sid)
    domain = str(c.get("physics_domain") or "")
    if domain:
        tags.append(f"domain:{slugify(domain)}")
    primary = c.get("primary_topic") or {}
    if isinstance(primary, dict) and primary.get("name"):
        tags.append(f"primary-topic:{slugify(primary['name'])}")
    for item in c.get("secondary_topics") or []:
        if isinstance(item, dict) and item.get("name"):
            tags.append(f"secondary-topic:{slugify(item['name'])}")
    for item in c.get("solution_models") or []:
        if isinstance(item, dict) and item.get("name"):
            tags.append(f"model:{slugify(item['name'])}")
    for item in c.get("skills") or []:
        if isinstance(item, dict) and item.get("id"):
            tags.append(f"skill:{slugify(item['id'])}")
    difficulty = c.get("difficulty") or {}
    if isinstance(difficulty, dict) and isinstance(difficulty.get("level"), int):
        tags.append(f"difficulty:{difficulty['level']}")
    return sorted(set(tags))


def derive_question(question: dict, taxonomy: dict) -> dict:
    c = question.get("classification")
    if not isinstance(c, dict):
        return question
    names = names_from_classification(c, taxonomy)
    question["course"] = names["course"]
    question["unit"] = names["unit"]
    question["topic"] = names["topic"]
    question["subtopics"] = names["subtopics"]
    question["knowledge_points"] = [
        str(item.get("name"))
        for item in (c.get("knowledge_points") or [])
        if isinstance(item, dict) and item.get("name")
    ]
    question["solution_models"] = [
        str(item.get("name"))
        for item in (c.get("solution_models") or [])
        if isinstance(item, dict) and item.get("name")
    ]
    question["skills"] = [
        str(item.get("id"))
        for item in (c.get("skills") or [])
        if isinstance(item, dict) and item.get("id")
    ]
    difficulty = c.get("difficulty") or {}
    question["difficulty"] = difficulty.get("level") if isinstance(difficulty, dict) else None

    custom = [
        str(tag) for tag in (question.get("tags") or [])
        if not any(str(tag).startswith(prefix) for prefix in GENERATED_PREFIXES)
    ]
    question["tags"] = custom + [tag for tag in derived_tags(question, taxonomy) if tag not in custom]
    c["derived_fields_version"] = "1.0"
    question["classification"] = c
    return question


def derive(data: dict, taxonomy: dict) -> dict:
    questions = data.get("questions")
    if not isinstance(questions, list):
        raise ValueError("questions.json must contain a top-level questions array")
    for question in questions:
        if isinstance(question, dict):
            derive_question(question, taxonomy)
    return data


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("questions", type=Path)
    p.add_argument("--taxonomy", required=True, type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    data = json.loads(args.questions.read_text(encoding="utf-8"))
    taxonomy = json.loads(args.taxonomy.read_text(encoding="utf-8"))
    derive(data, taxonomy)
    out = args.output or args.questions
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Derived semantic fields/tags for {len(data.get('questions') or [])} question(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
