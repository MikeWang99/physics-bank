# Answer extraction contract · v2.7

## Two distinct source modes

**Key only:** If the source gives only `17. C`, store:
```json
{"answer":{"kind":"key_only","label":"C","text":null,"evidence":"official-key","source":{"file":"assets/source/answer-key.pdf","page":2,"authority":"official"}}}
```
Do not generate a solution from model physics reasoning when the answer source is only an option. Never store boilerplate such as `Official answer: C` or `C, according to the AAPT answer key` in student-facing `answer.text`. Source attribution belongs ONLY in `answer.source`, `answer.provenance`, or the compact `answer.evidence` machine field. Legacy `{label,text:null,evidence}` records remain compatible.

**Worked/image source:** A provided answer may contain a label, source explanation, derivation, formulas, graphs, figures and signatures. Preserve the unedited source PDF/image under `assets/source`. Visually compare the source rather than interpreting OCR gaps as missing explanations. Separate exactly:

1. `answer.label`: the official option, if any.
2. `answer.text`: only real instructional explanation/derivation transcribed from the source, with `$...$` math syntax. Do not paraphrase, embellish or replace missing reasoning.
3. `answer.asset_ids`: independently cropped instructional answer figures (role `answer`).
4. `answer.layout_blocks`: text/figure blocks in original source reading order; each figure exactly once; text blocks must reproduce `answer.text` without omission.
5. `answer.source` and `answer.extraction`: original answer document, page, optional bbox, review method and raw source text for audit.
6. `answer.excluded_non_instructional`: signed record of page decorations omitted from learner display; each item has `kind`, `source_bbox` and `reason`.

Example:
```json
{
  "answer": {
    "kind": "worked_solution", "label": "B",
    "text": "Resolve the forces along the incline. $ma=mg\\sin\\theta$.",
    "evidence": "official-explanation",
    "source": {"file":"assets/source/solutions.pdf","page":12,"bbox":[40,70,530,390]},
    "extraction": {"method":"source-page-visual","reviewed":true,"raw_source_text":"...original transcription..."},
    "asset_ids": ["q017-answer-diagram-01"],
    "layout_blocks": [
      {"type":"text","text":"Resolve the forces along the incline."},
      {"type":"figure","asset_id":"q017-answer-diagram-01"},
      {"type":"text","text":"$ma=mg\\sin\\theta$."}
    ],
    "layout_review": {"reviewed":true,"method":"source-page-visual"},
    "excluded_non_instructional": [
      {"kind":"signature","source_bbox":[450,350,520,375],"reason":"Author signature, not instructional text"}
    ]
  },
  "asset_ids": ["q017-answer-diagram-01"]
}
```

Corresponding `assets.json` entry:
```json
{
  "id":"q017-answer-diagram-01", "role":"answer",
  "file":"assets/answers/q017/diagram-01.png",
  "owners":["q017"],
  "source":{"file":"assets/source/solutions.pdf","page":12,"bbox":[92,154,350,290]},
  "reviewed":true,
  "crop":{"reviewed":true,"review_sha256":"<sha256>","review_source_sha256":"<sha256>",
          "reviewed_source_bbox":[92,154,350,290],"source_neighborhood_reviewed":true,
          "review_method":"source-page-halo+final-file"}
}
```

## Image workflow

Keep the source image/PDF untouched. Segment option/paragraphs/equations/figures by visually comparing the source. Render each *semantic diagram* directly from the original source via `render_source_asset.py`; do not combine it with author credits or unrelated solution text. Inspect the halo plus final diagram, then seal with `seal_asset_review.py --confirm-source-neighborhood`. Answer image asset IDs must appear in both question `asset_ids` and `answer.asset_ids`; answer figures go ONLY in answer layout blocks, not question stem layout blocks.

**Signatures/watermarks:** Remove from *canonical instructional prose* only when clearly noninstructional. Record the source bbox and the reason. The unedited source remains archived. When a signature overlaps diagram labels, cannot be cleanly separated, or may encode information, keep the source visual and require manual review. Never inpaint or delete equations, labels or steps.

**Validation:** A worked solution must have reviewed answer extraction; illustrated solutions must have reviewed ordered layout blocks and source-sealed images. For uncertain answer text or diagrams, set the question review flag and do not publish. Key-only answers have no fabricated solution prose. Strict `validate_bank.py` checks these rules. Optional focused command:
```bash
python scripts/validate_answer_content.py question-bank/questions.json --assets question-bank/assets.json
```

## Web publisher

The existing frontend supports a fixed single `solutionImage`, not arbitrary interleaved answer narrative. Publisher preserves the complete answer in `question_versions.metadata.physicsBank.answer` and the images as version-bound `question_assets.role=answer`; blocks unsupported complex answer layout by default. It never invents `Official answer: A.` for key-only answers.
