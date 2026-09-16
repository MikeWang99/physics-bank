# Question-bank schema and asset manifest · v2.2

Paths are relative to the bundle root. The schema keeps text provenance, source year, visual provenance, and visual-choice ownership explicit.

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
      "source_pages": [3],
      "content_format": "markdown+latex",
      "context": "",
      "stem": "Which graph is correct?",
      "choices": [
        {"label": "A", "text": "", "asset_ids": ["fma-2016-q005-choice-A-01"]},
        {"label": "B", "text": "", "asset_ids": ["fma-2016-q005-choice-B-01"]}
      ],
      "answer": {"text": null, "label": null, "evidence": "not-provided"},
      "knowledge_points": ["graph interpretation"],
      "asset_ids": [
        "fma-2016-q005-choice-A-01",
        "fma-2016-q005-choice-B-01"
      ],
      "extraction": {"method": "pdf-text-layer", "text_reviewed": true, "confidence": 0.98},
      "requires_manual_review": false,
      "review_reasons": []
    }
  ]
}
```

## Exam year contract

Every published question has one canonical four-digit `year` integer and the same value in `source.year`. `tags` also contains `year:YYYY`. `year_evidence` records how the year was established. Never infer year from question content.

## Asset records

Stem/shared figure:

```json
{
  "id": "fma-2016-q005-stem-01",
  "file": "assets/figures/fma-2016-q005-stem-01.png",
  "source": {"file": "assets/source/2016_Fma_exam.pdf", "page": 3},
  "role": "stem",
  "owners": ["fma-2016-q005"],
  "reviewed": true,
  "crop": {"render_zoom": 6, "method": "box+autotrim", "reviewed": true}
}
```

Choice figure:

```json
{
  "id": "fma-2016-q005-choice-A-01",
  "file": "assets/choices/fma-2016-q005/A-01.png",
  "source": {"file": "assets/source/2016_Fma_exam.pdf", "page": 3},
  "role": "choice",
  "choice_label": "A",
  "choice_index": 1,
  "owners": ["fma-2016-q005"],
  "reviewed": true,
  "crop": {
    "render_zoom": 6,
    "method": "box+autotrim",
    "reviewed": true,
    "isolated_choice": true
  }
}
```

## Choice asset contract

- A final `choice` asset belongs to exactly one question.
- It has one uppercase `choice_label` matching a real entry in `question.choices`.
- `choice_index` is a positive integer. It is `1` for the normal one-image-per-option case.
- Final files live under `assets/choices/<question-id>/` and use `<LABEL>-<NN>.<ext>`.
- The matching choice object contains the asset ID in `choices[].asset_ids`.
- The same asset ID also remains in the question's top-level `asset_ids` for downstream compatibility.
- `crop.isolated_choice: true` means the final crop was visually checked to contain only that semantic option and no neighboring option image/label/prose.
- A combined multi-option strip/grid is never a valid final choice asset.
- If an option has multiple independent images, use unique indices (`A-01`, `A-02`, ...).
- A figure shared by all options is a `stem` or `shared` asset, not duplicated as four choice assets.

Valid asset roles remain `stem`, `choice`, `shared`. `reviewed: true` means the final file itself was visually inspected after the last modification.

Always retain an `answer` object. Only populate answers from official/user-supplied evidence unless the user explicitly requests solutions. Mathematical source remains Markdown+LaTeX.
