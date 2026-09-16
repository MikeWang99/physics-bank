---
name: physics-bank
description: Build source-faithful, validated physics question banks from exam PDFs, with deterministic text extraction, explicit review gates, traceable source pages, exam-year metadata, and visually reviewed diagram assets.
---

# Physics Bank v2

Build a reusable, auditable question bank. The governing rule is **source fidelity first**: the model may enrich metadata, but it must not silently repair, shorten, paraphrase, or guess source text or source metadata.

## Required output

Create a `question-bank/` bundle containing:

- `questions.json` using schema version `2.0`.
- `assets.json` using schema version `2.0`.
- `assets/source/` with source papers supplied by the user.
- `assets/figures/` with only final reviewed figure files.
- `extraction/raw_pages.json` and `extraction/question_drafts.json` as the audit trail.

Every published question must contain a canonical four-digit `year` and a matching `year:YYYY` tag. Example: a question extracted from a 2016 exam paper uses `"year": 2016` and includes `"year:2016"` in `tags`.

Read `references/text-extraction.md` and `references/asset-manifest.md` before execution.

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

   # or, when the source year is known but not safely inferable from the filename:
   python "$SKILL_DIR/scripts/stamp_exam_year.py" \
     question-bank/extraction/question_drafts.json --year 2016
   ```

   The script writes `year`, `source.year`, `year_evidence`, and `year:YYYY` in `tags`. Missing or ambiguous years become manual-review items; never guess the year from physics content.

4. Inspect `question_drafts.json` and the rendered/source pages. Resolve every `requires_manual_review` item. If a PDF is scan-only or the text layer is corrupted, visually transcribe from the page image; record the method and keep the raw draft for comparison.
5. Preserve `raw_source_text`, `source_pages`, original numbering, choices, shared context, and year metadata. Shared textual setup must be copied into each final question's `context` so every question is self-contained.
6. Only after visual/text comparison set `extraction.text_reviewed: true`.

Never infer omitted clauses from physics knowledge. If a symbol, sentence, or exam year cannot be established confidently from source evidence, keep the question in manual review instead of completing it from memory.

## Stage B — semantic enrichment (runs after Stage A in the same task)

Create stable final IDs, normalize math to `markdown+latex`, add course/unit/topic/subtopic/difficulty/skills/tags when supported by the source/context, and attach answer evidence. Preserve the canonical `year` field and its `year:YYYY` tag. Missing official answers remain `not-provided`; do not solve merely to fill the field.

Stage B may normalize whitespace and mathematical notation but must preserve meaning and all conditions. Compare the final stem/choices against Stage A before publication.

## Figure pipeline

1. Discover candidates independently of captions:

   ```bash
   python "$SKILL_DIR/scripts/discover_pdf_assets.py" source.pdf \
     --outdir "$TMPDIR/question-bank-discovery" --zoom 6
   ```

2. Determine ownership only after question boundaries exist. Classify each final asset as `stem`, `choice`, or `shared`.
3. For each crop, use `blocks → mark → preview → visual inspection → box/autotrim` as needed. `crop_figure.py` backups are recovery artifacts, not final deliverables.
4. Open the **final file after the last modification**. Verify labels, axes, arrowheads, endpoints, dimensions, option labels, scale information, and that no prose/answer/footer has leaked in.
5. Set asset `reviewed: true` only after that final inspection. Choice assets require `choice_label`.

A detection script finding no candidates is not evidence that no diagram exists. Scan the relevant question regions visually, especially for full-page raster/scanned PDFs.

## Final hard gate

Run both validators:

```bash
python "$SKILL_DIR/scripts/validate_bank.py" question-bank/questions.json \
  --assets question-bank/assets.json \
  --strict --require-text-review \
  --report question-bank/validation-report.json

python "$SKILL_DIR/scripts/validate_year_metadata.py" \
  question-bank/questions.json \
  --report question-bank/year-validation-report.json
```

Do not present a bank as complete if either validation fails. Fix the failing question/asset/year metadata or leave it explicitly pending review.

## Stability rules

- Never skip Stage A and jump directly from PDF to polished JSON.
- Never publish a question without a verified four-digit `year` plus matching `year:YYYY` tag.
- Prefer a four-digit year from the source filename/document metadata. A two-digit year such as `16` may map to 2016 only when it appears unambiguously in an exam-like source filename; otherwise require `--year` or manual review.
- Never use only page screenshots as question content when readable text can be represented structurally.
- Never discard cross-page continuation text.
- Never hide uncertainty by lowering confidence without a review flag.
- Never mark a crop reviewed before inspecting the final post-crop file.
- Never publish unresolved asset IDs, orphan assets, duplicate IDs, or unreviewed text.
- Re-running on the same PDF should preserve stable IDs, source boundaries, and year metadata unless a human review intentionally corrects them.
