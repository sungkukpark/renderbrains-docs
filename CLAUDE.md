# CLAUDE.md

This repository is a shared knowledge system for **2+ team members** built around three responsibilities:

- **Obsidian** for fast authoring and personal knowledge capture
- **Quarto / QMD** for structured publishing
- **CLI automation** for synchronization, validation, and build/deploy workflows

This file defines the **source-of-truth rules** for humans and AI agents working in the repository.

---

## 1. Repository purpose

The repository supports all of the following at once:

1. Personal knowledge capture inside Obsidian
2. Shared team documentation
3. Publishable technical docs, guides, reports, and references
4. Repeatable conversion from Obsidian-style notes to Quarto-ready documents

The design principle is:

> **Author freely, publish deliberately, automate the gap.**

---

## 2. Core operating model

Treat the repository as having two layers:

### A. Authoring layer
Used inside Obsidian.

- Fast capture
- Wiki links
- Daily notes
- Personal drafts
- Incomplete thought fragments allowed

### B. Publishing layer
Used by Quarto and the docs site.

- Structured content only
- Stable paths
- Required frontmatter
- Clean outbound links
- Build must succeed without manual cleanup

### Rule
Do **not** let publishing rules destroy authoring speed.
Do **not** let authoring freedom break published docs.

The CLI is responsible for bridging the two.

---

## 3. Recommended repository layout

```text
knowledge-base/
├── CLAUDE.md
├── README.md
├── .gitignore
├── _quarto.yml
├── pyproject.toml                  # if Python CLI is used
├── package.json                   # if Node tooling is also used
│
├── vault/                         # Obsidian authoring area
│   ├── inbox/                     # quick capture, unrefined notes
│   ├── notes/                     # evergreen notes
│   ├── projects/                  # project-specific working notes
│   ├── daily/                     # daily notes
│   ├── people/                    # people / meeting context
│   ├── references/                # raw reference notes
│   ├── templates/                 # note templates
│   └── assets/                    # images, diagrams, attachments
│
├── docs/                          # generated or curated publishable content
│   ├── index.qmd
│   ├── guides/
│   ├── references/
│   ├── architecture/
│   ├── decisions/
│   └── reports/
│
├── scripts/
│   ├── sync.py                    # vault -> docs sync
│   ├── lint.py                    # metadata / links / style checks
│   ├── build.py                   # local build wrapper
│   └── utils/
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── publish.yml
│
└── tmp/                           # ignored local outputs
```

---

## 4. Ownership of directories

### `vault/`
Primary authoring area.
Humans work here first.

### `docs/`
Publishable layer.
Can be:
- generated from `vault/`
- manually curated when a document requires stricter structure

### `scripts/`
Automation only.
Any repetitive task should be moved here instead of being done manually.

### `vault/assets/`
All local attachments go here unless a published document needs a dedicated asset folder.

---

## 5. Canonical workflow

### Daily workflow
1. Create or edit notes in `vault/`
2. Use Obsidian wiki links normally
3. Mark notes that should be published
4. Run sync
5. Run lint
6. Build Quarto site
7. Commit changes
8. Open PR if team review is required

### Command workflow
```bash
python scripts/sync.py
python scripts/lint.py
quarto render
```

If a task is performed more than twice, add a wrapper command:

```bash
make sync
make lint
make build
make preview
```

or

```bash
just sync
just lint
just build
just preview
```

---

## 6. Publishing contract

A note is publishable only if all required conditions are met.

### Required publish metadata
Every publishable note must contain frontmatter:

```yaml
---
title: "Deferred Rendering Overview"
slug: "deferred-rendering-overview"
publish: true
category: "architecture"
tags:
  - rendering
  - graphics
status: "stable"
updated: 2026-04-06
owner: "team"
---
```

### Required fields
- `title`
- `slug`
- `publish`
- `category`
- `status`
- `updated`

### Optional fields
- `tags`
- `summary`
- `owner`
- `source`
- `aliases`

### Allowed `status` values
- `draft`
- `review`
- `stable`
- `archived`

### Allowed `publish` values
- `true`
- `false`

### Rule
If `publish: true`, the note must pass lint and build.

---

## 7. File naming rules

### In `vault/`
Humans may use readable names during authoring, but stable names are preferred.

Recommended:
```text
Deferred Rendering.md
Frame Graph.md
Shader Compilation Pipeline.md
```

### In `docs/`
Use deterministic slugs only:

```text
deferred-rendering-overview.qmd
frame-graph.qmd
shader-compilation-pipeline.qmd
```

### Slug rule
- lowercase
- kebab-case
- ASCII preferred
- no spaces
- no dates in filename unless the document is explicitly date-scoped

---

## 8. Link rules

### Authoring links in `vault/`
Use Obsidian wiki links:

```md
[[Frame Graph]]
[[Shader Compilation Pipeline]]
[[Deferred Rendering|deferred rendering]]
```

### Publishing links in `docs/`
Must become normal Markdown links:

```md
[Frame Graph](../architecture/frame-graph.qmd)
[Shader Compilation Pipeline](../guides/shader-compilation-pipeline.qmd)
```

### Source-of-truth rule
Humans author wiki links.
The sync script resolves and converts them.

### Hard rule
Do not manually maintain both wiki links and publish links in the same source note unless there is a strong reason.

---

## 9. Sync behavior requirements

`scripts/sync.py` is expected to do the following:

1. Read notes from `vault/`
2. Detect notes with `publish: true`
3. Normalize frontmatter
4. Convert wiki links to publishable relative links
5. Copy or transform content into `docs/`
6. Preserve stable slugs
7. Copy referenced assets when needed
8. Fail loudly on ambiguous links

### Ambiguous link policy
If `[[Rendering]]` matches multiple source notes, sync must fail with a useful error.
Never guess silently.

### Missing link policy
If a publishable note links to a missing target:
- lint fails
- build may proceed only if configured explicitly
- default behavior should be failure for shared docs quality

---

## 10. Asset rules

### Default location
```text
vault/assets/
```

### Naming convention
```text
YYYYMMDD-short-description.ext
```

Example:
```text
20260406-frame-graph-overview.png
```

### Asset usage
- Prefer relative paths
- Prefer compressed images
- Avoid duplicate attachments with slightly different names
- Avoid storing generated binaries unless necessary

### Publish rule
Assets referenced by published docs must be copied or resolved into publish-safe paths.

---

## 11. Notes classification model

All notes should fit one of these types:

### `inbox`
Unprocessed capture. Never published directly.

### `note`
Evergreen concept note. Can be published after cleanup.

### `project`
Working note tied to a team project.

### `reference`
Externally sourced material summarized internally.

### `decision`
Architecture or process decision. Should publish to `docs/decisions/`.

### `report`
Time-bound analysis or summary.

Use frontmatter when possible:

```yaml
type: "decision"
```

---

## 12. Team collaboration rules

This repository is shared. Optimization for one person must not create ambiguity for everyone else.

### Required collaboration rules
- Do not rewrite another person's note structure without reason
- Do not rename published slugs casually
- Do not force personal note habits into the publish layer
- Prefer additive edits over destructive reorganization
- Use PR review for structural changes

### For 2+ member teams
At least one of these must be true:
- branch + PR review for `docs/`
- branch + PR review for `scripts/`
- CI required on `main`

Recommended:
- direct commits allowed in `vault/inbox/`
- PR required for `docs/`, `scripts/`, `_quarto.yml`, CI files

---

## 13. Branching strategy

Recommended branches:

- `main` — stable, publishable
- `dev` — optional integration branch
- `feature/<name>` — work branch
- `docs/<name>` — documentation-specific branch
- `infra/<name>` — CI, tooling, or repo structure changes

### Merge rule
Anything that affects publishing behavior should be reviewed before merge.

---

## 14. Pull request checklist

Before merging, ensure:

- sync completes successfully
- lint passes
- Quarto render passes
- no broken links
- no orphaned assets added
- frontmatter fields valid
- changed slugs intentional
- published navigation still makes sense

Suggested PR template:

```md
## Summary
What changed?

## Scope
- vault
- docs
- scripts
- CI

## Checks
- [ ] sync passed
- [ ] lint passed
- [ ] build passed
- [ ] links checked
- [ ] slug changes reviewed
```

---

## 15. Linting rules

`lint.py` should validate at minimum:

1. required frontmatter exists
2. `slug` uniqueness
3. `publish` notes contain titles
4. `updated` date format valid
5. `status` value valid
6. no duplicate output paths
7. no unresolved wiki links in publishable output
8. no broken relative asset references
9. no banned folders in publish output

### Nice-to-have checks
- title/slug mismatch warnings
- overly long filenames
- empty headings
- TODO markers in stable docs
- duplicate notes with different names but same slug intent

---

## 16. Quarto conventions

### `_quarto.yml` baseline
```yaml
project:
  type: website
  output-dir: _site

website:
  title: "Team Knowledge Base"
  search: true
  navbar:
    left:
      - href: docs/index.qmd
        text: Home
      - href: docs/guides/index.qmd
        text: Guides
      - href: docs/architecture/index.qmd
        text: Architecture
      - href: docs/references/index.qmd
        text: References

format:
  html:
    toc: true
    number-sections: true
    smooth-scroll: true
```

### Rule
Quarto config is shared infrastructure. Edit carefully and review changes.

---

## 17. Minimal sync mapping policy

This is the minimum mapping expected between Obsidian notes and publishable docs.

| Source in `vault/` | Output in `docs/` |
|---|---|
| `vault/notes/*.md` | `docs/references/` or `docs/guides/` |
| `vault/projects/*.md` | `docs/guides/` or `docs/reports/` |
| `vault/references/*.md` | `docs/references/` |
| `vault/daily/*.md` | not published by default |
| `vault/inbox/*.md` | never published |

### Daily note rule
Daily notes are source material, not final documents.

---

## 18. Recommended sync heuristics

When converting a note to publishable form:

1. Use frontmatter `slug` as output filename
2. If no slug exists, derive from title
3. Resolve category to output folder
4. Convert `[[Wiki Links]]` to relative links
5. Strip Obsidian-only blocks if necessary
6. Preserve fenced code blocks exactly
7. Preserve callouts where Quarto supports them
8. Warn on embeds that cannot be rendered cleanly

### Obsidian features requiring special handling
- embeds: `![[...]]`
- block references
- canvas files
- Dataview syntax
- plugin-specific syntax

Default rule:
If a feature is not publish-safe, the sync step must either:
- transform it explicitly, or
- fail with a clear message

Never silently drop meaningful content.

---

## 19. AI agent instructions

When an AI agent edits this repository, it must follow these rules.

### The agent must
- preserve existing repository structure unless asked to refactor it
- prefer minimal, reversible changes
- update `updated:` when materially changing publishable docs
- avoid renaming files unless necessary
- keep frontmatter valid
- keep generated and source layers conceptually separate
- explain infra-impacting changes in commit or PR text

### The agent must not
- invent slugs arbitrarily if one already exists
- rewrite note voice unnecessarily
- flatten the whole repository into a single docs folder
- move assets casually
- convert all Markdown to QMD unless requested
- remove wiki links from source notes purely for stylistic reasons

### On ambiguity
Prefer preserving structure over aggressively “cleaning up.”

---

## 20. Human authoring guidance

### For quick capture
Put incomplete ideas in:

```text
vault/inbox/
```

### For reusable knowledge
Move refined notes to:

```text
vault/notes/
```

### For team-visible documentation
Mark with:

```yaml
publish: true
```

### For formal documentation
Ensure:
- meaningful title
- stable slug
- summary at top
- links resolved
- assets referenced cleanly

---

## 21. Example publishable source note

```md
---
title: "Frame Graph"
slug: "frame-graph"
publish: true
category: "architecture"
tags:
  - rendering
  - engine
status: "review"
updated: 2026-04-06
owner: "graphics-team"
summary: "Overview of frame graph motivation, structure, and scheduling model."
---

# Frame Graph

A frame graph organizes render passes and resource lifetimes explicitly.

See also [[Deferred Rendering Overview]] and [[Shader Compilation Pipeline]].

## Why it matters

- Makes dependencies visible
- Enables transient resource reuse
- Improves scheduling clarity
```

### Expected published output
```md
---
title: "Frame Graph"
---

# Frame Graph

A frame graph organizes render passes and resource lifetimes explicitly.

See also [Deferred Rendering Overview](../architecture/deferred-rendering-overview.qmd) and [Shader Compilation Pipeline](../guides/shader-compilation-pipeline.qmd).

## Why it matters

- Makes dependencies visible
- Enables transient resource reuse
- Improves scheduling clarity
```

---

## 22. Example Makefile

```makefile
sync:
\tpython scripts/sync.py

lint:
\tpython scripts/lint.py

build:
\tquarto render

preview:
\tquarto preview

check: sync lint build
```

---

## 23. Example CI pipeline expectations

CI should run on every PR affecting:
- `docs/**`
- `vault/**`
- `scripts/**`
- `_quarto.yml`

### CI stages
1. environment setup
2. dependency install
3. sync
4. lint
5. quarto render
6. artifact upload or publish preview

### Publish stage
Only on merge to `main`.

---

## 24. Change management policy

These changes are considered **structural** and require extra review:

- changing repo layout
- changing frontmatter schema
- changing slug generation
- changing sync output folders
- changing Quarto navbar or section structure
- changing CI behavior
- changing how wiki links resolve

These changes are considered **content-level** and usually lighter-weight:

- editing note body text
- adding references
- clarifying explanations
- adding examples
- fixing typos
- updating summaries

---

## 25. Recommended initial implementation plan

### Phase 1 — stable baseline
- create repo structure
- define frontmatter contract
- add Quarto config
- add sync script
- add lint script
- add CI

### Phase 2 — publish quality
- resolve assets cleanly
- generate section indexes
- improve navigation
- add broken-link reporting

### Phase 3 — scale for team usage
- templates
- onboarding docs
- note type presets
- dashboards / reports
- decision log workflow

---

## 26. Non-goals

This repository is **not** intended to be:

- a fully free-form dumping ground with no curation
- a replacement for issue tracking
- a place for opaque binary storage
- a system where published docs are edited manually without traceability
- a wiki with uncontrolled page naming and silent duplication

---

## 27. Final rules to protect the system

1. The source note and published doc are related but not identical responsibilities.
2. Shared docs require stable metadata.
3. Ambiguous links are bugs, not conveniences.
4. Automation must remove toil, not hide problems.
5. Human writing speed matters.
6. Publish quality matters.
7. When these goals conflict, fix the tooling rather than blaming the authors.

---

## 28. First commands to run in a new clone

```bash
python scripts/sync.py
python scripts/lint.py
quarto render
```

If all three pass, the repository is in a healthy state.

---

## 29. Maintainer note

If this file and the actual repository behavior diverge, update one of them immediately.
Do not let the rules and the tooling drift apart.
