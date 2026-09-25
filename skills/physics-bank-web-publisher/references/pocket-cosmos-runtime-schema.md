# Pocket Cosmos runtime schema · observed production contract

This contract was derived from the live Pocket Cosmos Next.js Practice API/bundle and production Supabase schema.

## Canonical persistence

### public.questions

Stable identity and set ordering:

- `id text primary key`
- `practice_set_id text`
- `legacy_question_id text`
- `status active|retired`
- `position integer`

Pocket Cosmos uses:

```text
questions.id = <practice-set-id>::<local-question-id>
```

There is a unique constraint on `(practice_set_id, legacy_question_id)`.

### public.question_versions

Immutable content versions:

- `id uuid`
- `question_id text`
- `version integer > 0`
- `stem text`
- `choices jsonb`
- `answer jsonb`
- `explanation text`
- `metadata jsonb`
- `source_year integer`
- `source_ref text`
- `content_hash text`

Important unique constraints:

- `(question_id, version)`
- `(question_id, content_hash)` when hash is non-null

Never update an old content version to represent new content.

### public.question_assets

Version-bound Storage relationships:

- `question_version_id uuid`
- `role stem|figure|choice|answer|source`
- `storage_bucket text`
- `storage_path text`
- `choice_key text|null`
- `sort_order integer`
- `metadata jsonb`

Current runtime recognizes metadata slots including:

- `image`
- `supportingImages`
- `choices.image`
- `choices.images`
- `solutionImage`
- `assets`

New publisher rows should avoid legacy duplicate download rows unless explicitly requested.

## Current API shape

`GET /api/practice/sets/:id` returns:

```json
{
  "set": {
    "id": "...",
    "system": "ap-physics-1",
    "practiceKind": "mcq",
    "chapter": 1,
    "chapterTitle": "Kinematics",
    "title": "...",
    "label": "...",
    "subtitle": "...",
    "eyebrow": "...",
    "description": "...",
    "sources": [],
    "steps": []
  },
  "access": "..."
}
```

A runtime step can contain:

- `id`
- `mode`
- `title`
- `prompt`
- `source`
- `context`
- `choices`
- `tags`
- `difficulty`
- `specialtyTags`
- `correctAnswer`
- `solution`
- `criteria`
- `maxScore`
- `answerNudge`
- `image`
- `supportingImages`
- `assets`
- `questionVersionId`

The current client renders prompt first, then `image`, then `supportingImages`, then choices.

## Metadata v2 proposed by this Skill

```json
{
  "formatVersion": 2,
  "practiceSet": {
    "id": "...",
    "label": "...",
    "title": "...",
    "system": "...",
    "category": "...",
    "practiceKind": "...",
    "chapter": 1,
    "chapterTitle": "...",
    "subtitle": "...",
    "eyebrow": "...",
    "description": "...",
    "sources": []
  },
  "practiceStep": {
    "id": "...",
    "mode": "multiple_choice",
    "title": "Question 1",
    "prompt": "...",
    "context": "...",
    "choices": [],
    "tags": [],
    "difficulty": 3,
    "specialtyTags": [],
    "source": "...",
    "criteria": [],
    "maxScore": 1,
    "correctAnswer": "A",
    "solution": "..."
  },
  "physicsBank": {
    "schema": "physics-bank-web-publish/v1",
    "questionId": "...",
    "bankSchemaVersion": "2.0",
    "classification": {},
    "layoutBlocks": [],
    "layoutReview": {},
    "sourcePages": [],
    "source": {},
    "extraction": {},
    "assetIds": [],
    "renderCompatibility": {}
  }
}
```

The current frontend consumes `practiceSet/practiceStep`. `physicsBank` retains the complete canonical information for future renderer/filter upgrades.
