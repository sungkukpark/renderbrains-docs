# RenderBrains Docs

Official documentation and knowledge base for [RenderBrains](https://renderbrains.com).

Built on **Obsidian + Quarto + Python CLI**:

- `vault/` — personal Obsidian workspace (local only, gitignored)
- `wiki/` — LLM-synthesized knowledge pages (git-tracked)
- `tutorials/`, `how-to/`, `reference/`, `explanation/` — published site content (Quarto/QMD)
- `scripts/` — sync, lint, and build automation

The published site is available at **[renderbrains.com](https://renderbrains.com)**.

---

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python toolchain)
- [Quarto](https://quarto.org/docs/get-started/) (v1.4+)
- [Obsidian](https://obsidian.md/) (optional, for vault authoring)

### Setup

```bash
git clone https://github.com/sungkukpark/renderbrains-docs.git
cd renderbrains-docs
uv sync
```

### Run the full pipeline

```bash
make run
```

This runs `sync → lint → build` in sequence. All three must pass before committing to `main`.

### Individual commands

```bash
make sync      # wiki/ → site content conversion
make lint      # validate frontmatter and links
make build     # quarto render → _site/
make preview   # quarto preview (live reload)
make clean     # remove _site/ and __pycache__
```

---

## Repository Layout

```
renderbrains-docs/
├── index.qmd               # Home page
├── tutorials/              # Step-by-step learning guides
├── how-to/                 # Task-oriented recipes
├── reference/              # API references and lookup material
├── explanation/            # Concepts, architecture, ADRs
├── assets/                 # Site assets (logo, CSS, favicon)
│
├── wiki/                   # LLM-maintained knowledge pages (git-tracked)
│   ├── index.md            # Wiki page catalog
│   ├── log.md              # Operation log (append-only)
│   └── *.md                # Synthesized knowledge pages
│
├── vault/                  # Personal Obsidian workspace (local only, gitignored)
│   ├── inbox/              # Quick capture — never published
│   ├── references/         # Raw reference notes (immutable)
│   ├── daily/              # Daily notes
│   └── assets/             # Images, diagrams, attachments
│
├── scripts/
│   ├── sync.py             # wiki/ → site content sync
│   ├── lint.py             # metadata and link validation
│   └── utils/
│       └── frontmatter.py  # shared parsing utilities
│
├── _quarto.yml             # Quarto site configuration
├── CLAUDE.md               # Publishing rules and contract
├── ARCHITECT.md            # LLM wiki operating pattern
├── pyproject.toml          # Python dependencies
├── Makefile                # Convenience commands
└── .github/workflows/      # CI/CD
```

---

## Writing Notes in Obsidian

### Where to write

| Location | Purpose | Git-tracked |
|---|---|---|
| `vault/inbox/` | Quick capture, raw ideas | No |
| `vault/references/` | External source notes | No |
| `vault/daily/` | Daily notes | No |
| `wiki/` | Refined knowledge pages ready to publish | Yes |

Write freely in `vault/` using any Obsidian feature. When a note is ready to share with the team or publish to the site, move it to `wiki/` and add the required frontmatter.

### Required frontmatter

Every note in `wiki/` that should be published must include:

```yaml
---
title: "Frame Graph"
slug: "frame-graph"
publish: true
category: "explanation"
status: "stable"
updated: 2026-04-06
---
```

| Field | Required | Description |
|---|---|---|
| `title` | Yes | Human-readable title |
| `slug` | Yes | URL-safe identifier (lowercase, kebab-case) |
| `publish` | Yes | Set to `true` to publish |
| `category` | Yes | One of the four allowed values below |
| `status` | Yes | One of the four allowed values below |
| `updated` | Yes | Last modified date (`YYYY-MM-DD`) |
| `summary` | No | One-sentence description shown in listings |
| `tags` | No | List of topic tags |
| `owner` | No | Responsible team or person |

**Allowed `category` values:**

| Value | Output folder | Use for |
|---|---|---|
| `tutorials` | `tutorials/` | Step-by-step learning guides |
| `how-to` | `how-to/` | Task-specific recipes |
| `reference` | `reference/` | API docs, config schemas, lookup tables |
| `explanation` | `explanation/` | Concepts, architecture, ADRs |

**Allowed `status` values:** `draft`, `review`, `stable`, `archived`

### Slug rules

- Lowercase, kebab-case, ASCII only
- Must be unique across all published notes
- Used as the output filename: `slug: "frame-graph"` → `explanation/frame-graph.qmd`
- Do not change a published slug casually — it breaks existing links

### Wiki links

Use Obsidian wiki links freely inside `vault/` and `wiki/`:

```md
See also [[Frame Graph]] and [[Shader Compilation Pipeline|shader pipeline]].
```

The sync script resolves these to proper relative links automatically:

```md
See also [Frame Graph](../explanation/frame-graph.qmd) and [shader pipeline](../how-to/shader-compilation-pipeline.qmd).
```

**Rules:**
- If the link target has no matching note → warning, rendered as plain text
- If the link target matches multiple published notes → **sync fails** (ambiguous link; fix by giving notes unique titles)
- If the link target exists but `publish: false` → warning, rendered as plain text

### Image embeds

Obsidian image embeds are converted to Markdown image syntax:

```md
![[20260406-frame-graph-overview.png]]
→ ![20260406-frame-graph-overview.png](../assets/20260406-frame-graph-overview.png)
```

Place all images in `vault/assets/`. The sync script copies referenced assets to the publish output automatically.

**Naming convention for assets:** `YYYYMMDD-short-description.ext`

### Note embeds (not supported)

Obsidian note embeds (`![[SomeNote]]`) cannot be rendered in Quarto. The sync script replaces them with an HTML comment and prints a warning:

```html
<!-- EMBED: SomeNote (not rendered in published output) -->
```

Remove or rewrite note embeds before setting `publish: true`.

### Obsidian features that do not sync

| Feature | Behavior |
|---|---|
| Note embeds `![[Note]]` | Replaced with HTML comment — rewrite manually |
| Block references `![[Note#^block]]` | Not supported — rewrite manually |
| Dataview queries | Not rendered — remove before publishing |
| Canvas files | Not published |
| Callouts `> [!note]` | Supported in Quarto — sync preserves them |
| Fenced code blocks | Fully preserved |

### Full example note

```md
---
title: "Frame Graph"
slug: "frame-graph"
publish: true
category: "explanation"
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

![[20260406-frame-graph-overview.png]]
```

---

## Publishing Workflow

### 1. Author in vault/ or wiki/

Write freely in `vault/`. When a note is stable enough to publish, place it in `wiki/` with the required frontmatter.

### 2. Run sync

```bash
make sync
```

The sync script:
- Finds all `publish: true` notes in `wiki/`
- Converts `[[wiki links]]` to relative Quarto links
- Copies output to `{category}/{slug}.qmd`
- Copies referenced assets to `assets/`
- **Fails loudly** on ambiguous links or missing required fields

### 3. Run lint

```bash
make lint
```

Validates:
- Required frontmatter fields present and valid
- `status` and `category` values allowed
- `updated` date is valid ISO format (`YYYY-MM-DD`)
- Slug uniqueness across all published output
- No unresolved wiki links remaining in published files

### 4. Build and preview

```bash
make preview   # live preview at localhost:4200
make build     # full render to _site/
```

### 5. Commit and PR

- Direct commits allowed in `wiki/` for minor updates
- PR required for site content, `scripts/`, `_quarto.yml`, CI files
- CI runs `sync → lint → build` on every PR

---

## Publishing Contract

A note is publishable only when:

1. `publish: true` is set
2. All required frontmatter fields are present and valid
3. `make sync` completes without errors
4. `make lint` exits 0

Notes in `vault/inbox/` and `vault/daily/` are **never published**, even with `publish: true`.

---

## Contributing

1. Branch from `main`: `git checkout -b docs/your-topic`
2. Author in `vault/`, refine in `wiki/`
3. Run `make run` — all three steps must pass
4. Open a PR; at least one team review required for changes to site content, `scripts/`, or `_quarto.yml`

---

## CI/CD

- **CI** runs on every PR touching `wiki/`, site content folders, `scripts/`, or `_quarto.yml`
- **Publish** runs on merge to `main`, deploying to AWS S3 (`renderbrains.com`)

See `.github/workflows/` for details.
