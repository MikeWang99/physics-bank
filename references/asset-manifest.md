# Question-bank asset manifest

Use a stable question manifest plus an asset manifest. Paths are relative to the bundle root.

```json
{
  "questions": [
    {
      "id": "fma-2009-q05",
      "source": {"file": "assets/source/2009_Fma_exam.pdf", "page": 3, "original_number": "5"},
      "stem": "...",
      "choices": [{"label": "A", "text": "..."}],
      "answer": {"label": "C", "evidence": "official-key"},
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

Valid `role` values are `stem`, `choice`, and `shared`. A choice asset also contains `choice_label`. A `shared` asset lists all question IDs in `owners`. Do not store absolute paths, raw page screenshots, or unreviewed candidates as final assets.
