# Storage and versioning contract

## Buckets

Current production buckets relevant to this Skill:

- `question-assets` — private runtime question media
- `source-documents` — private source-document bucket, currently separate from runtime assets

v1.0 publishes question figures/choice images only to `question-assets`.

## Immutable content-addressed object path

```text
banks/<practice-set-id>/assets/<asset-id>-<sha256-prefix>.<ext>
```

Example:

```text
banks/fma-competition-bank/assets/fma-2024-q017-choice-a-01-91c3d5f8e1af.png
```

Do not overwrite a changed file at the old path. Supabase recommends new object paths rather than overwriting CDN-cached assets.

## Upload sequence

1. compile + validate bundle;
2. calculate/verify every asset SHA-256;
3. upload all missing content-addressed objects with `x-upsert: false`;
4. only after all uploads succeed, execute the database transaction.

An upload failure must stop DB publication.

## Credentials

Server-side only:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Never put the service-role key into Next.js client bundles, public env vars, logs, Git, or generated metadata.

## Database mutation sequence

Database rows are applied in one transaction after storage succeeds.

Historical `question_versions` are immutable.

A version is reused when:

```text
question_id + content_hash
```

already exists.

A new version is appended only when the canonical publish content changes.

## Orphans

If storage succeeds but the SQL transaction fails, content-addressed orphan objects are safe and may be reused by the retry. Do not delete them automatically during a failed publish.
