# Question-bank asset manifest

Use a stable question manifest plus an asset manifest. Paths are relative to the bundle root.

```json
{
  "questions": [
    {
      "id": "fma-2009-q05",
      "source": {"file": "assets/source/2009_Fma_exam.pdf", "page": 3, "original_number": "5"},
      "content_format": "markdown+latex",
      "stem": "A charge moves through a potential difference $V$.",
      "choices": [{"label": "A", "text": "..."}],
      "answer": {"text": null, "label": null, "evidence": "not-provided"},
      "knowledge_points": ["circular motion", "angular momentum"],
      "asset_ids": ["fma-2009-p03-stem-01"]
    }
  ]
}
```

```json
{
  "assets": [
    {
      "id": "fma-2009-p03-stem-01",
      "file": "assets/figures/fma-2009-p03-stem-01.png",
      "source": {"file": "assets/source/2009_Fma_exam.pdf", "page": 3},
      "role": "stem",
      "owners": ["fma-2009-q05"],
      "crop": {"render_zoom": 6, "method": "box+autotrim", "reviewed": true},
      "notes": "Orbit labels A, B, C retained; question prose excluded."
    }
  ]
}
```

Valid `role` values are `stem`, `choice`, and `shared`. A choice asset also contains `choice_label`. A `shared` asset lists all question IDs in `owners`.

## Answer and mathematical-content rules

Always retain an `answer` object. If an official or user-supplied answer exists, populate `text` and/or `label` and identify its evidence. Otherwise use `{"text": null, "label": null, "evidence": "not-provided"}`. Do not generate an independent solution merely to populate the field.

Set `content_format` to `markdown+latex`. Store inline mathematics as `$...$` and display mathematics as `$$...$$`; do not rely on Unicode superscripts, plain-text approximations, or renderer-specific HTML as the canonical mathematical source. JSON alone does not render LaTeX: downstream viewers and PDF generators must apply a Markdown renderer with MathJax, KaTeX, or equivalent support.

Do not store absolute paths, raw page screenshots, or unreviewed candidates as final assets. The delivered bundle contains only source papers, final figures, and manifests; discovery output and `_debug/` crop history remain temporary unless an audit package is explicitly requested.
