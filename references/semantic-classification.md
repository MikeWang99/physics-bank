# Semantic classification contract · v2.5

The question bank must preserve not only the source question, but also a **structured, auditable interpretation of what the question requires a student to know and do**.

The model must read the complete self-contained question before classification: `context`, `stem`, choices, and every relevant stem/shared/choice figure. Do not classify from keywords alone.

## Governing principle

Classification is a separate stage after source extraction and visual reconstruction:

```text
complete question evidence
→ semantic analysis
→ physics model identification
→ curriculum mapping
→ skill / knowledge / difficulty classification
→ derive searchable mirrors + tags
→ semantic validation
→ publish
```

Do not store hidden chain-of-thought. Store short **classification evidence** that makes each decision auditable.

## Bank-level curriculum taxonomy

Every published bank includes:

```text
question-bank/classification-taxonomy.json
```

Use the official course syllabus when one is supplied. Otherwise create a stable bank taxonomy from the competition/course structure and generic physics hierarchy.

Example:

```json
{
  "schema": "physics-bank-curriculum-taxonomy/v1",
  "course": {
    "id": "fma",
    "name": "F=ma",
    "basis": "competition-bank-taxonomy"
  },
  "units": [
    {
      "id": "dynamics",
      "name": "Dynamics",
      "topics": [
        {
          "id": "newtons-laws",
          "name": "Newton's Laws",
          "subtopics": [
            {"id": "friction", "name": "Friction"},
            {"id": "connected-bodies", "name": "Connected bodies"}
          ]
        }
      ]
    }
  ]
}
```

IDs must be stable lowercase slugs. A question maps by ID so `Dynamics`, `dynamics`, and `Forces & Dynamics` cannot silently become three different categories.

## Canonical question classification

Each final question contains:

```json
{
  "classification": {
    "schema": "physics-question-classification/v1",
    "status": "reviewed",
    "curriculum": {
      "course_id": "fma",
      "unit_id": "dynamics",
      "topic_id": "newtons-laws",
      "subtopic_ids": ["friction"]
    },
    "physics_domain": "mechanics",
    "primary_topic": {
      "name": "Newton's second law",
      "evidence": "The required quantity is obtained by constructing the net-force equation for the body."
    },
    "secondary_topics": [
      {
        "name": "Friction",
        "evidence": "The friction force is part of the force model but is not the main organizing principle."
      }
    ],
    "knowledge_points": [
      {
        "name": "Static friction adjusts up to its limiting value",
        "role": "required",
        "evidence": "The force must be determined from equilibrium/impending-motion conditions rather than assumed to equal μN."
      }
    ],
    "solution_models": [
      {
        "name": "Newton's second law",
        "kind": "governing_law",
        "role": "primary",
        "evidence": "The final unknown follows from the net-force equation."
      }
    ],
    "skills": [
      {
        "id": "model_selection",
        "evidence": "The student must decide which force model applies before calculating."
      },
      {
        "id": "free_body_diagram",
        "evidence": "Correct force identification is necessary to build the governing equation."
      }
    ],
    "difficulty": {
      "level": 3,
      "drivers": [
        "requires model selection before calculation",
        "requires more than direct substitution"
      ]
    },
    "confidence": 0.91,
    "review": {
      "reviewed": true,
      "method": "model-semantic-analysis"
    }
  }
}
```

## Primary vs secondary

A **primary topic/model** is the organizing idea without which the solution cannot be formed.

A **secondary topic** may appear in the setup or provide one relationship, but does not organize the solution.

Do not tag a topic merely because a word/object appears in the stem. A circular track does not automatically make the primary topic `Circular Motion`; a friction coefficient does not automatically make `Friction` primary.

## Solution models

Use the model kinds from `references/semantic-taxonomy.json`.

This dimension answers: **What bridge turns the givens into the unknown?**

Examples:

- Newton's second law → `governing_law`
- momentum conservation → `conservation_law`
- rigid-string equal acceleration → `constraint`
- ideal gas law → `constitutive_relation`
- centripetal acceleration → `kinematic_relation`
- geometric similarity → `geometry`

A question may have multiple solution models. Mark at least one `role: primary`.

## Knowledge points

Knowledge points answer: **What must the student know?**

Use concise canonical statements, not broad labels. Prefer:

`static friction adjusts up to a limiting value`

over:

`friction`

## Skills

Skills answer: **What must the student do?**

Use only IDs defined in `references/semantic-taxonomy.json`. Do not invent near-synonyms.

## Difficulty

Difficulty is 1–5 and follows the reference rubric. Judge the **required solution path**, not text length, arithmetic ugliness, or whether the question looks intimidating.

Every difficulty must include at least one concrete driver.

## Evidence and confidence

Evidence is a short audit statement, not hidden reasoning. It should identify the observable solution requirement that supports the classification.

If the full question/figure is insufficient to classify confidently:

- set `status: "review"`
- set `review.reviewed: false`
- add `semantic_classification_uncertain` to `review_reasons`
- do not publish in strict mode

Confidence below the reference threshold requires review.

## Derived mirrors and tags

`classification` is canonical. Run `scripts/derive_semantic_tags.py` to populate compatibility/search fields:

- `course`
- `unit`
- `topic`
- `subtopics`
- `knowledge_points`
- `solution_models`
- `skills`
- `difficulty`
- prefixed `tags`

Examples:

```text
course:fma
unit:dynamics
topic:newtons-laws
subtopic:friction
domain:mechanics
model:newtons-second-law
skill:model-selection
difficulty:3
year:2024
```

Do not manually curate these derived prefixes. The validator checks that they match the canonical classification.
