# ARCHITECT.md

This file defines how an LLM agent operates the personal wiki inside this repository.
It is inspired by Andrej Karpathy's [llm-wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Read this file before doing any work in `vault/`. For publishing rules, see `CLAUDE.md`.

---

## Core idea

The wiki is a **persistent, compounding knowledge artifact**. Every new source enriches
existing pages rather than requiring re-discovery at query time. The LLM maintains the
wiki; the human curates sources, asks questions, and interprets meaning.

---

## Repository layers

| Layer | Location | Owner | Description |
|---|---|---|---|
| Raw Sources | `vault/inbox/`, `vault/references/` | Human | Immutable source material. Never modified after ingestion. |
| The Wiki | `vault/notes/`, `vault/projects/`, `vault/people/` | LLM | Synthesized, cross-linked knowledge pages. |
| Schema | `CLAUDE.md`, `ARCHITECT.md` | Both | Rules governing authoring, publishing, and wiki operations. |
| Publishing | `docs/` + Quarto | LLM + CI | Team-visible output, a subset of the wiki. |

### Rule
Do not conflate layers. A raw source in `vault/inbox/` stays there unchanged.
The wiki page that synthesizes it lives in `vault/notes/`.

---

## Bookkeeping files

Two files must always exist and be kept current.

### `vault/index.md`
Content catalog of every wiki page. Organized by category. One line per page.

```
## notes
- [[Frame Graph]] — Overview of render pass organization and resource lifetime management.
- [[Shader Compilation Pipeline]] — Stages from HLSL source to runtime PSO.

## projects
- [[RenderBrains v2 Rewrite]] — Ongoing rewrite tracking decisions and blockers.

## people
- [[John Kim]] — Graphics engineer, owns the frame graph subsystem.
```

**When to update:** After every Ingest, add or revise entries for touched pages.
The LLM uses this file to locate relevant pages quickly without scanning the entire vault.

### `vault/log.md`
Append-only chronological record. Never edit past entries.

```
2026-04-07 [INGEST] "Deferred Rendering Survey" (vault/references/deferred-rendering-survey.md)
  → updated: Frame Graph, Deferred Rendering Overview
  → created: Tile-Based Deferred Rendering

2026-04-07 [QUERY] "What are the tradeoffs between forward and deferred rendering?"
  → synthesized from: Frame Graph, Deferred Rendering Overview
  → new page: Forward vs Deferred Rendering Tradeoffs

2026-04-08 [LINT] 3 orphan pages found, 1 contradiction flagged (see lint output)
```

---

## Operations

### Ingest

Use when: a new source has been placed in `vault/inbox/` or `vault/references/`.

Steps:
1. Read `vault/index.md` to understand existing wiki coverage.
2. Read the source file fully.
3. Identify which existing wiki pages it extends, contradicts, or relates to.
4. Write or update relevant pages in `vault/notes/`. Use `[[Wiki Links]]` freely.
   One source commonly touches 10–15 pages; that is expected.
5. If a page does not exist yet, create it with a brief stub and a `## Sources` section.
6. Update `vault/index.md` — add new pages, revise summaries of updated pages.
7. Append an `[INGEST]` entry to `vault/log.md` listing the source and affected pages.

Rules:
- Never modify the source file.
- Never silently drop content — if something cannot be represented cleanly, note it
  in the wiki page with a `> Note:` callout.
- Contradictions between sources must be flagged explicitly in the affected wiki page.

### Query

Use when: the user asks a question that should be answered from accumulated knowledge.

Steps:
1. Read `vault/index.md` to identify relevant pages.
2. Read those pages in full.
3. Synthesize an answer with inline citations (e.g., `[[Frame Graph]]`).
4. If the answer is substantial and likely to be asked again, write it as a new
   wiki page in `vault/notes/`.
5. Append a `[QUERY]` entry to `vault/log.md` listing the question, pages consulted,
   and whether a new page was created.

### Lint

Use when: the user asks for a wiki health check, or periodically after heavy ingestion.

Steps:
1. Scan all pages in `vault/notes/` (use `vault/index.md` as the starting map).
2. Report:
   - Contradictions between pages
   - Orphan pages (not linked from any other page)
   - Stale claims (pages not updated after related sources were ingested)
   - Missing cross-references (pages that should link to each other but don't)
   - Pages referenced in `[[Wiki Links]]` that do not exist
3. Suggest specific sources to investigate for identified gaps.
4. Append a `[LINT]` entry to `vault/log.md` with a summary of findings.

---

## Publishing bridge

The wiki and the published docs site are separate concerns.

To promote a wiki page to the published site:
1. Add required frontmatter (see `CLAUDE.md` §6 and `vault/templates/publishable-note.md`).
2. Set `publish: true`.
3. Run `make check` — sync → lint → build must all pass.
4. Commit and push. CI deploys automatically on merge to `main`.

Not every wiki page needs to be published. Publish deliberately.

---

## LLM agent rules

**Before any operation:**
- Read `vault/index.md` first. Always.

**During any operation:**
- Prefer updating existing wiki pages over creating new ones.
- Use `[[Wiki Links]]` for all cross-references within `vault/`.
- Keep wiki page titles stable — renaming breaks links.

**After any operation:**
- Append to `vault/log.md`. Always. Do not skip this step.

**Never:**
- Modify files in `vault/inbox/` or `vault/references/`.
- Delete wiki pages without the user's explicit instruction.
- Flatten wiki pages into a single document.
- Write to `docs/` directly — use `make sync` instead.

---

## Quick reference

```bash
# Run a full wiki health check (sync + lint + build)
make check

# Preview the published site locally
make preview

# Common workflow after adding sources to vault/inbox/
# 1. Ask the LLM to Ingest the new source(s)
# 2. Review the updated wiki pages in Obsidian
# 3. If any should be published: add frontmatter, make check, commit
```

---

## File locations at a glance

```text
vault/
├── index.md              ← wiki catalog (LLM-maintained)
├── log.md                ← operation log (append-only)
├── inbox/                ← new sources land here (human drops files)
├── references/           ← curated external references (immutable)
├── notes/                ← evergreen wiki pages (LLM-maintained)
├── projects/             ← project working notes
├── people/               ← people and team context
├── daily/                ← daily notes (never published)
├── assets/               ← images and attachments
└── templates/
    └── publishable-note.md
```
