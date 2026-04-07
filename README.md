# RenderBrains Docs

Official documentation and knowledge base for [RenderBrains](https://renderbrains.com).

Built on **Obsidian + Quarto + Python CLI**:

- `vault/` — internal authoring space (Obsidian)
- `docs/` — publishable documentation (Quarto/QMD)
- `scripts/` — sync, lint, and build automation

The published site is available at **[docs.renderbrains.com](https://docs.renderbrains.com)**.

---

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python toolchain)
- [Quarto](https://quarto.org/docs/get-started/) (v1.4+)
- [Obsidian](https://obsidian.md/) (optional, for vault authoring)

### Setup

```bash
git clone https://github.com/renderbrains/renderbrains-docs.git
cd renderbrains-docs
uv sync
```

### Run the full pipeline

```bash
make check
```

This runs `sync → lint → build` in sequence. All three must pass before committing to `main`.

### Individual commands

```bash
make sync      # vault/ → docs/ conversion
make lint      # validate frontmatter and links
make build     # quarto render → _site/
make preview   # quarto preview (live reload)
make clean     # remove _site/ and __pycache__
```

---

## Repository Layout

```
renderbrains-docs/
├── vault/                  # Obsidian authoring area (author here first)
│   ├── inbox/              # Quick capture — never published directly
│   ├── notes/              # Evergreen concept notes
│   ├── projects/           # Project-specific working notes
│   ├── daily/              # Daily notes — not published by default
│   ├── people/             # People / meeting context
│   ├── references/         # Raw reference notes
│   ├── assets/             # Images, diagrams, attachments
│   └── templates/          # Note templates
│
├── docs/                   # Published documentation (Quarto)
│   ├── index.qmd
│   ├── guides/
│   ├── architecture/
│   ├── references/
│   └── decisions/
│
├── scripts/
│   ├── sync.py             # vault → docs sync
│   ├── lint.py             # metadata and link validation
│   └── utils/
│       └── frontmatter.py  # shared parsing utilities
│
├── _quarto.yml             # Quarto site configuration
├── pyproject.toml          # Python dependencies
├── Makefile                # Convenience commands
└── .github/workflows/      # CI/CD
```

---

## Authoring Workflow

### 1. Create a note in vault/

Write freely in Obsidian. Use wiki links (`[[Title]]`), daily notes, and inbox capture without concern for publish format.

### 2. Mark a note for publishing

Add or update the frontmatter:

```yaml
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
```

**Required fields:** `title`, `slug`, `publish`, `category`, `status`, `updated`

**Allowed `status` values:** `draft`, `review`, `stable`, `archived`

**Allowed `category` values:** `architecture`, `guides`, `references`, `decisions`, `reports`

### 3. Run sync

```bash
make sync
```

The sync script:
- Finds all `publish: true` notes in `vault/`
- Converts `[[wiki links]]` to relative Quarto links
- Copies output to `docs/{category}/{slug}.qmd`
- Warns on Obsidian-specific syntax that cannot be rendered cleanly
- **Fails loudly** on ambiguous links (same title, multiple notes)

### 4. Run lint

```bash
make lint
```

Validates:
- Required frontmatter fields present
- `status` and `category` values are valid
- `updated` date is valid ISO format
- Slug uniqueness across all output files
- No unresolved `[[wiki links]]` in published output

### 5. Build and preview

```bash
make preview   # live preview at localhost:4200
make build     # full render to _site/
```

### 6. Commit and PR

- Direct commits allowed in `vault/inbox/`
- PR required for `docs/`, `scripts/`, `_quarto.yml`, CI files
- CI runs `sync → lint → build` on every PR

---

## Publishing Contract

A note is publishable only when:

1. `publish: true` is set
2. All required frontmatter fields are present and valid
3. `make sync` succeeds without errors
4. `make lint` exits 0

Notes in `vault/inbox/` and `vault/daily/` are **never published**.

---

## Link Rules

| Context | Format |
|---|---|
| Authoring in vault/ | `[[Frame Graph]]` |
| Published in docs/ | `[Frame Graph](../architecture/frame-graph.qmd)` |

The sync script converts wiki links automatically. Do not manually maintain both forms in the same source note.

---

## Contributing

1. Branch from `main`: `git checkout -b docs/your-topic`
2. Author in `vault/`
3. Run `make check` — all three steps must pass
4. Open a PR with the [PR template](.github/pull_request_template.md)
5. At least one team review required for changes to `docs/`, `scripts/`, or `_quarto.yml`

---

## CI/CD

- **CI** runs on every PR touching `docs/`, `vault/`, `scripts/`, or `_quarto.yml`
- **Publish** runs on merge to `main`, deploying to GitHub Pages (or Cloudflare Pages)

See `.github/workflows/` for details.
