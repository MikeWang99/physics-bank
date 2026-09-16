# Question-bank schema and asset manifest · v2

Paths are relative to the bundle root. The v2 schema keeps text provenance, source year, and visual provenance explicit.

```json
{
  "schema_version": "2.0",
  "questions": [
    {
      "id": "fma-2016-q005",
      "year": 2016,
      "year_evidence": {"method": "source-four-digit", "value": "assets/source/2016_Fma_exam.pdf"},
      "tags": ["year:2016"],
      "source": {"file": "assets/source/2016_Fma_exam.pdf", "page": 3, "original_number": "5", "year": 2016},
      "source_pages": [3, 4],
      "content_format": "markdown+latex",
      "context": "Shared setup copied here so the question is self-contained.",
      "stem": "A charge moves through a potential difference $V$.",
      "choices": [{"label": "A", "text": "..."}],
      "answer": {"text": null, "label": null, "evidence": "not-provided"},
      "knowledge_points": ["electric potential"],
      "asset_ids": ["fma-2016-p003-stem-01"],
      "extraction": {"method": "pdf-text-layer", "text_reviewed": true, "confidence": 0.98},
      "requires_manual_review": false,
      "review_reasons": []
    }
  ]
}
```

## Exam year contract

Every published question has one canonical four-digit `year` integer and the same value in `source.year`. `tags` also contains `year:YYYY` for simple filtering. `year_evidence` records how the year was established.

Preferred evidence order:

1. explicit user/source metadata (`--year 2016`);
2. a unique four-digit year in the source filename/path;
3. an unambiguous two-digit year in an exam-like filename, e.g. `Fma_16_exam.pdf` → `2016`.

Do not infer the year from question content, syllabus style, or answer choices. Missing or conflicting source years remain manual-review items.

```json
{
  "schema_version": "2.0",
  "assets": [
    {
      "id": "fma-2016-p003-stem-01",
      "file": "assets/figures/fma-2016-p003-stem-01.png",
      "source": {"file": "assets/source/2016_Fma_exam.pdf", "page": 3},
      "role": "stem",
      "owners": ["fma-2016-q005"],
      "reviewed": true,
      "crop": {"render_zoom": 6, "method": "box+autotrim", "reviewed": true}
    }
  ]
}
```

Valid asset roles: `stem`, `choice`, `shared`. A choice asset **must** contain `choice_label`; a shared asset lists all owners. `reviewed: true` means the final file itself was visually inspected after the last crop/modification, not merely that a candidate was previewed earlier.

Always retain an `answer` object. Only populate answers from official/user-supplied evidence unless the user explicitly requests solutions. Mathematical source remains Markdown+LaTeX. Downstream renderers must either support the encountered LaTeX subset or fail explicitly; silently dropping commands is not acceptable.
