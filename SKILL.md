---
name: physics-bank
description: Build source-faithful, validated physics question banks from exam PDFs, preserving deterministic text provenance, exam-year metadata, independently reviewed visual assets, and the original narrative placement of every stem/shared figure.
---

# Physics Bank v2.4

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

Read `references/text-extraction.md`, `references/asset-manifest.md`, `references/choice-assets.md`, and `references/narrative-layout.md` before execution.

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
6. Preserve source geometry. `raw_pages.json` line bboxes are evidence for reading order; every final stem/shared asset must later record its source `page` and semantic PDF-point `bbox`.
7. Only after visual/text comparison set `extraction.text_reviewed: true`.

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

   Discovery is **non-authoritative**. Candidate rasters are only navigation/review aids. The detector expands graphic clusters to absorb nearby short text labels such as voltage values, symbols, axis labels, and units, but a candidate must never become the irreversible parent image for a published asset.

2. Determine ownership only after question boundaries exist. Classify stem-level assets as `stem` or `shared` and publish them under `assets/figures/`.
3. Choose the semantic region on the **original source page**, not on a discovery candidate. Record it in `assets.json -> source.page + source.bbox`.
4. Render the final asset directly from the original PDF:

   ```bash
   python "$SKILL_DIR/scripts/render_source_asset.py" source.pdf \
     --page <1-based-page> --bbox X0 Y0 X1 Y1 \
     --output question-bank/assets/figures/<asset>.png \
     --report "$TMPDIR/<asset>-source-review.json"
   ```

   This also produces a `_debug/*source-halo.png` preview with the kept bbox marked in source context. If it reports nearby short-text risks, enlarge the bbox. Only explicitly irrelevant text may be documented in `crop.ignore_nearby_text`.

5. Use `blocks → mark → preview → visual inspection → box/autotrim` only for cleanup **after** a source-faithful render. Any destructive recrop automatically invalidates an existing review seal.
6. Open both the **final file after the last modification** and the source-halo preview. Verify labels, axes, arrowheads, endpoints, dimensions, scale information, and that no neighboring prose/answer/footer leaked in.
7. Seal that exact reviewed state:

   ```bash
   python "$SKILL_DIR/scripts/seal_asset_review.py" \
     question-bank/assets.json --asset-id <asset-id> \
     --confirm-source-neighborhood
   ```

   The seal stores the final-image SHA-256, source-PDF SHA-256, and reviewed source bbox. Any later file/bbox/source change makes strict validation fail until the asset is reviewed and sealed again.
8. Reconstruct the original text/figure reading order in `question.layout_blocks`. Every figure block must carry a `source_anchor`; every stem/shared asset must appear exactly once.
9. Compare the reconstructed order against the rendered source page. Only then set `layout_review.reviewed: true` on the question.

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

## Narrative layout gate — mandatory in v2.3

The bank must preserve **where** each stem/shared visual occurs, not merely that it belongs to the question.

For any question with one or more `stem` / `shared` assets:

1. Record each asset's physical source location in `assets.json`:
   - `source.file`
   - `source.page`
   - `source.bbox: [x0, y0, x1, y1]`
2. Build ordered `question.layout_blocks` using only source-faithful `text` and `figure` blocks.
3. Ensure the concatenated text blocks preserve all of `context + stem`; do not omit prose merely because a figure interrupts it.
4. Give every figure block a `source_anchor`:
   - `question_start` / `question_end`, or
   - `before` / `after` with a short exact source phrase.
5. Set `question.layout_review = {"reviewed": true, "method": "..."}` only after visual comparison with the source page.

`choices[].asset_ids` remains the placement mechanism for visual answer choices; choice images do not belong in narrative `layout_blocks`.

Do not rely on downstream PDF generation to infer layout. `homework-pdf` already consumes `layout_blocks` as authoritative order, so the question bank must supply them correctly.



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

Do not present a bank as complete if validation fails. In v2.4 strict validation additionally rejects stale/missing visual-review seals, source-PDF changes after review, source-bbox changes after review, significant ink touching the outer crop border, source text/drawings/images that cross the bbox, likely short diagram labels just outside the bbox, stem/shared visuals without source bboxes, missing/incomplete narrative layout blocks, unreviewed layouts, duplicate/missing figure placement, invalid anchors, or layout text that no longer covers the complete context + stem.

## Stability rules

- Never skip Stage A and jump directly from PDF to polished JSON.
- Never publish a question without verified year metadata.
- Never use only page screenshots as question content when readable text can be represented structurally.
- Never discard cross-page continuation text.
- Never hide uncertainty by lowering confidence without a review flag.
- Never mark a crop reviewed before inspecting the final post-crop file **and its source-halo preview**, then sealing that exact state.
- Never create a published stem/shared asset by repeatedly cropping a discovery candidate; final pixels must come directly from the original PDF source bbox.
- Never rely on `reviewed: true` alone. A valid review requires matching image/source SHA-256 seals and the exact reviewed source bbox.
- **Never keep multiple answer options in one final choice-image file.**
- **Never place final choice images in `assets/figures/`; use `assets/choices/<question-id>/`.**
- **Never bind one choice asset to multiple questions.**
- Never publish unresolved asset IDs, orphan assets, duplicate IDs, or unreviewed text.
- Never publish a stem/shared visual without explicit source geometry and narrative placement.
- Never let a downstream renderer guess whether a figure belongs before or after a sentence.
- Re-running on the same PDF should preserve stable IDs, source boundaries, year metadata, choice-asset slots, source bboxes, and reviewed layout order unless human review intentionally corrects them.
