---
name: physics-bank
description: Build source-faithful, validated physics question banks from exam PDFs, with deterministic text extraction, explicit review gates, traceable source pages, exam-year metadata, and separately reviewed stem/choice visual assets.
---

# Physics Bank v2

Build a reusable, auditable question bank. The governing rule is **source fidelity first**: the model may enrich metadata, but it must not silently repair, shorten, paraphrase, merge, or guess source text, source metadata, or visual option content.

## Required output

Create a `question-bank/` bundle containing:

- `questions.json` using schema version `2.0`.
- `assets.json` using schema version `2.0`.
- `assets/source/` with source papers supplied by the user.
- `assets/figures/` with final reviewed stem/shared figures only.
- `assets/choices/<question-id>/` with final reviewed **individual choice images** only.
- `extraction/raw_pages.json` and `extraction/question_drafts.json` as the audit trail.

Every published question must contain a canonical four-digit `year` and a matching `year:YYYY` tag.

Read `references/text-extraction.md`, `references/asset-manifest.md`, and `references/choice-assets.md` before execution.

## Stage A — faithful extraction (mandatory; do not skip)

1. Inventory source PDFs and answer keys.
2. Run:

   ```bash
   python "$SKILL_DIR/scripts/extract_question_text.py" source.pdf \
     --outdir question-bank/extraction \
     --id-prefix <stable-prefix>
   ```

3. Stamp the exam year onto the drafts. If the source filename contains a unique year, let the script infer it. For opaque/ambiguous filenames, pass the known source year explicitly:

   ```bash
   python "$SKILL_DIR/scripts/stamp_exam_year.py" \
     question-bank/extraction/question_drafts.json

   python "$SKILL_DIR/scripts/stamp_exam_year.py" \
     question-bank/extraction/question_drafts.json --year 2016
   ```

4. Inspect `question_drafts.json` and the rendered/source pages. Resolve every `requires_manual_review` item. If a PDF is scan-only or the text layer is corrupted, visually transcribe from the page image; record the method and keep the raw draft for comparison.
5. Preserve `raw_source_text`, `source_pages`, original numbering, choices, shared context, and year metadata. Shared textual setup must be copied into each final question's `context` so every question is self-contained.
6. Only after visual/text comparison set `extraction.text_reviewed: true`.

Never infer omitted clauses from physics knowledge. If a symbol, sentence, or exam year cannot be established confidently from source evidence, keep the question in manual review instead of completing it from memory.

## Stage B — semantic enrichment

Create stable final IDs, normalize math to `markdown+latex`, add course/unit/topic/subtopic/difficulty/skills/tags when supported by source/context, preserve canonical year metadata, and attach answer evidence. Missing official answers remain `not-provided`; do not solve merely to fill the field.

Stage B may normalize whitespace and mathematical notation but must preserve meaning and all conditions. Compare final stem/choices against Stage A before publication.

## Figure pipeline

### Stem/shared figures

1. Discover candidates independently of captions:

   ```bash
   python "$SKILL_DIR/scripts/discover_pdf_assets.py" source.pdf \
     --outdir "$TMPDIR/question-bank-discovery" --zoom 6
   ```

2. Determine ownership only after question boundaries exist. Classify stem-level assets as `stem` or `shared` and publish them under `assets/figures/`.
3. For each crop, use `blocks → mark → preview → visual inspection → box/autotrim` as needed.
4. Open the **final file after the last modification**. Verify labels, axes, arrowheads, endpoints, dimensions, scale information, and that no neighboring prose/answer/footer leaked in.
5. Set `reviewed: true` only after that final inspection.

### Visual choice pipeline — mandatory when any option contains an image

Visual choices are first-class assets. **Never publish a combined A/B/C/D option strip or grid as one final asset.** Each semantic option image must be independently cropped and independently reviewed.

For each visual option:

1. Identify its owner question and choice label before cropping.
2. Crop that option independently. Exclude neighboring choice images and, when practical, exclude the printed A/B/C/D label itself because the label is represented structurally in JSON.
3. Run `blocks → mark → preview → visual inspection → crop` for that option alone.
4. Verify the final crop contains the complete intended option image and no content from any other option. Only then set:

   ```json
   {
     "role": "choice",
     "choice_label": "A",
     "choice_index": 1,
     "reviewed": true,
     "crop": {"reviewed": true, "isolated_choice": true}
   }
   ```

5. Add the asset ID to both:
   - the question's top-level `asset_ids` for downstream compatibility; and
   - the matching `choices[].asset_ids` entry for precise option binding.
6. Canonicalize the files and JSON links:

   ```bash
   python "$SKILL_DIR/scripts/organize_choice_assets.py" \
     question-bank/questions.json \
     --assets question-bank/assets.json \
     --apply \
     --report question-bank/choice-asset-report.json
   ```

Final choice files must live at:

```text
assets/choices/<question-id>/<LABEL>-<NN>.<ext>
```

Examples:

```text
assets/choices/fma-2016-q005/A-01.png
assets/choices/fma-2016-q005/B-01.png
assets/choices/fma-2016-q005/C-01.png
assets/choices/fma-2016-q005/D-01.png
```

If one option genuinely contains multiple independent images, give them unique positive `choice_index` values (`A-01`, `A-02`, ...). Do not use `choice_index` to represent neighboring answer options.

A diagram shared by all choices is **not** a choice asset; store it as `stem`/`shared`. A text+image option keeps its text in `choices[].text` and its image IDs in `choices[].asset_ids`.

A detection script finding no candidates is not evidence that no diagram exists. Scan relevant question/choice regions visually, especially for full-page raster/scanned PDFs.

## Final hard gate

Run all validators:

```bash
python "$SKILL_DIR/scripts/validate_bank.py" question-bank/questions.json \
  --assets question-bank/assets.json \
  --strict --require-text-review \
  --report question-bank/validation-report.json

python "$SKILL_DIR/scripts/validate_year_metadata.py" \
  question-bank/questions.json \
  --report question-bank/year-validation-report.json
```

Do not present a bank as complete if validation fails. In v2.2 strict validation also rejects visual choice assets that are combined, unreviewed, incorrectly bound, duplicated, shared across questions, or stored outside their canonical choice folder.

## Stability rules

- Never skip Stage A and jump directly from PDF to polished JSON.
- Never publish a question without verified year metadata.
- Never use only page screenshots as question content when readable text can be represented structurally.
- Never discard cross-page continuation text.
- Never hide uncertainty by lowering confidence without a review flag.
- Never mark a crop reviewed before inspecting the final post-crop file.
- **Never keep multiple answer options in one final choice-image file.**
- **Never place final choice images in `assets/figures/`; use `assets/choices/<question-id>/`.**
- **Never bind one choice asset to multiple questions.**
- Never publish unresolved asset IDs, orphan assets, duplicate IDs, or unreviewed text.
- Re-running on the same PDF should preserve stable IDs, source boundaries, year metadata, and choice-asset slots unless human review intentionally corrects them.
