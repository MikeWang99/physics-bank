---
name: physics-bank
description: Build traceable physics question banks from exam PDFs or local source packs, with question-level metadata and visually reviewed, high-resolution diagram assets. Use for extracting, organizing, adapting, or publishing physics question banks; not for a one-off worksheet with no reusable bank.
---

# Physics Bank · 物理题库

Build a reusable question bank, not a pile of copied page screenshots. Every question must retain its source provenance, answer, knowledge-point tags, and an asset record for every diagram it needs.

## Outcome contract

Create a `question-bank/` bundle whose `questions.json` records each question's ID, source PDF/page/original number, stem, choices, answer, explanation or answer-key source, knowledge points, and asset IDs. Keep source text and rendered assets under `assets/`; a question may reference a stem diagram, option diagram(s), or a shared asset. Preserve source wording unless the user authorizes adaptation.

Read [the asset-manifest reference](references/asset-manifest.md) before creating or changing a bank schema. If the requested result is a printable worksheet or diagnostic PDF, use the bank as source of truth and then follow the appropriate PDF/visual-QA workflow.

## Workflow

1. **Inventory the source.** Record source files and answer keys. Extract selectable text where reliable; otherwise mark the question for transcription/OCR review. Identify question boundaries before claiming figure ownership.
2. **Create the question records first.** Establish stable IDs, page/original question number, answer evidence, topic tags, and `asset_ids`. Do not embed a whole PDF-page screenshot when a stem and choices can be typeset.
3. **Discover candidate graphics independently of captions.** Research papers often have `Figure N`; exam PDFs commonly do not. Run:

   ```bash
   python "$SKILL_DIR/scripts/discover_pdf_assets.py" source.pdf --outdir question-bank/assets/discovery --zoom 6
   ```

   The script rasterizes candidate raster/vector clusters at 6x scale (about 432 DPI) and writes `candidates.json`. It provides hints only; it does not decide what a question owns. Associate each candidate with the question region containing it or directly preceding it. Check whether shared information belongs to several questions.
4. **Review candidate ownership visually.** Classify every kept item as `stem`, `choice`, or `shared`; reject page chrome, captions, question prose, answer text, and incidental decorative marks. For option diagrams, record the option label and use separate assets when that is clearer than one composite image.
5. **Crop safely.** Use the included crop utility against a candidate PNG. It preserves the original as `_debug/<name>.bak` before destructive edits and retains marked/preview iterations.

   ```bash
   python "$SKILL_DIR/scripts/crop_figure.py" blocks candidate.png
   python "$SKILL_DIR/scripts/crop_figure.py" mark candidate.png --box X0 Y0 X1 Y1
   python "$SKILL_DIR/scripts/crop_figure.py" preview candidate.png --box X0 Y0 X1 Y1
   # inspect the preview; only then:
   python "$SKILL_DIR/scripts/crop_figure.py" box candidate.png --box X0 Y0 X1 Y1
   python "$SKILL_DIR/scripts/crop_figure.py" autotrim candidate.png --pad 12
   ```

   Use `split` for independent panels or option diagrams. Do not use `autotrim` to remove real neighboring content; use `box` after a reviewed preview.
6. **Visual QA is mandatory.** Open each final crop after the last modification. Check that all labels, axes, arrowheads, curve endpoints, dimensions, option letters, and scale information are visible; that no question prose/answers are included; and that whitespace is intentional. Re-crop on any failure. For a rebuilt diagram, use a vector diagram workflow rather than a source crop whenever the original is illegible or the geometry is pedagogically important.
7. **Validate the bundle.** Every `asset_id` in `questions.json` must resolve to an existing file and every asset must have one or more owners (or `shared_with`). Verify answers against an official key where available; flag independent derivations. Keep student-facing exports free of internal source notes unless the user asks to show them.

## Decision rules

- Render PDFs at 6x by default for asset work; lower resolution is acceptable only when the user explicitly prioritizes speed and the final use remains legible.
- A detection script finding no figures is not evidence that the PDF has no diagrams. Continue with question-region review and vector/raster candidates.
- Treat preliminary boxes as proposals. Never batch-commit them without previews and visual inspection.
- Keep original crops and audit previews under `_debug/`; do not silently overwrite a source asset.
- If a figure is reused by adjacent questions, use one `shared` asset with multiple owners rather than duplicate files.
- For diagrams embedded inside choices, keep the choice label in metadata; do not infer the label merely from left-to-right position when the layout is ambiguous.

## Dependencies and portability

This Skill is self-contained except for Python packages listed in `requirements.txt`. Before first use on a new computer, install them into an isolated Python environment, then copy this whole `physics-bank` folder into that computer's `~/.codex/skills/`. The crop utility derives from Microsoft ResearchStudio's MIT-licensed implementation; see [third-party notices](references/THIRD_PARTY_LICENSES.md).
