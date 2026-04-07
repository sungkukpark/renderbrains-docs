#!/usr/bin/env python3
"""
lint.py — Documentation Quality Gate
======================================
Validates publishable vault/ notes and docs/ output files.

Usage:
    python scripts/lint.py [--vault VAULT_DIR] [--docs DOCS_DIR]

Exit codes:
    0  All checks pass.
    1  One or more validation errors found (all errors printed before exit).
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

# Allow running as `python scripts/lint.py` from repo root
sys.path.insert(0, str(Path(__file__).parent))
from utils.frontmatter import parse

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent

REQUIRED_PUBLISH_FIELDS: list[str] = [
    "title",
    "slug",
    "publish",
    "category",
    "status",
    "updated",
]

ALLOWED_STATUS: frozenset[str] = frozenset({"draft", "review", "stable", "archived"})
ALLOWED_CATEGORY: frozenset[str] = frozenset(
    {"architecture", "guides", "references", "decisions", "reports"}
)

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# wiki link pattern: [[...]] — should NOT appear in published docs/ output
WIKI_LINK_RE = re.compile(r"\[\[[^\[\]]+\]\]")

# Never-publish directories (relative to vault/)
NEVER_PUBLISH_DIRS: set[str] = {"inbox", "daily"}

# Banned folder names in docs/ output
BANNED_IN_DOCS: set[str] = {"inbox", "daily", "tmp"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_in_code_block(lines: list[str], target_line_idx: int) -> bool:
    """Return True if target_line_idx is inside a fenced code block."""
    in_fence = False
    fence_marker: str | None = None
    for i, line in enumerate(lines):
        if i == target_line_idx:
            return in_fence
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = True
                fence_marker = stripped[:3]
        else:
            if fence_marker and stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = None
    return in_fence


def _check_wiki_links_in_body(body: str, file_path: Path) -> list[str]:
    """Return errors for any [[wiki links]] found outside code blocks in body."""
    errors: list[str] = []
    lines = body.split("\n")
    for i, line in enumerate(lines, 1):
        for m in WIKI_LINK_RE.finditer(line):
            if not _is_in_code_block(lines, i - 1):
                errors.append(
                    f"{file_path}: line {i}: unresolved wiki link '{m.group()}' "
                    "in published output. Run `make sync` to resolve, or remove the link."
                )
    return errors


def _check_asset_references(body: str, docs_dir: Path, file_path: Path) -> list[str]:
    """Return errors for broken relative asset references."""
    errors: list[str] = []
    image_re = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    for m in image_re.finditer(body):
        href = m.group(1).strip()
        if href.startswith("http://") or href.startswith("https://"):
            continue
        # Resolve relative to the file's location
        resolved = (file_path.parent / href).resolve()
        if not resolved.exists():
            errors.append(
                f"{file_path}: broken asset reference '{href}' "
                f"(resolved to {resolved}). Add the file or fix the path."
            )
    return errors


# ---------------------------------------------------------------------------
# Phase A: Validate publishable vault/ notes
# ---------------------------------------------------------------------------


def lint_vault(vault_dir: Path) -> list[str]:
    """Validate all vault/ notes with `publish: true`."""
    errors: list[str] = []

    for md_file in sorted(vault_dir.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Cannot read {md_file}: {exc}")
            continue

        try:
            meta, body = parse(text)
        except ValueError as exc:
            errors.append(f"{md_file}: {exc}")
            continue

        if meta.get("publish") is not True:
            continue

        # Check never-publish directories
        try:
            rel_parts = md_file.relative_to(vault_dir).parts
        except ValueError:
            rel_parts = ()
        if rel_parts and rel_parts[0] in NEVER_PUBLISH_DIRS:
            errors.append(
                f"{md_file}: has `publish: true` but lives in "
                f"'{rel_parts[0]}/' which is never published. "
                "Remove `publish: true` or move the note."
            )
            continue

        # Required fields
        missing = [f for f in REQUIRED_PUBLISH_FIELDS if f not in meta]
        if missing:
            errors.append(
                f"{md_file}: missing required publish fields: {', '.join(missing)}"
            )
            # Continue to catch additional errors even if fields are missing
            if "status" in missing and "category" in missing:
                continue

        # Validate status
        status = meta.get("status")
        if status is not None and str(status) not in ALLOWED_STATUS:
            errors.append(
                f"{md_file}: invalid status '{status}'. "
                f"Allowed values: {sorted(ALLOWED_STATUS)}"
            )

        # Validate category
        category = meta.get("category")
        if category is not None and str(category) not in ALLOWED_CATEGORY:
            errors.append(
                f"{md_file}: invalid category '{category}'. "
                f"Allowed values: {sorted(ALLOWED_CATEGORY)}"
            )

        # Validate slug format
        slug = meta.get("slug")
        if slug is not None:
            if not SLUG_RE.match(str(slug)):
                errors.append(
                    f"{md_file}: slug '{slug}' is not valid kebab-case "
                    "(lowercase, alphanumeric, hyphens only, no leading/trailing hyphens)."
                )

        # Validate updated date
        updated = meta.get("updated")
        if updated is not None:
            updated_str = str(updated)
            if not DATE_RE.match(updated_str):
                errors.append(
                    f"{md_file}: invalid `updated` date '{updated_str}'. "
                    "Expected ISO format YYYY-MM-DD."
                )
            else:
                try:
                    date.fromisoformat(updated_str)
                except ValueError:
                    errors.append(
                        f"{md_file}: `updated` value '{updated_str}' is not a valid calendar date."
                    )

        # Validate title not empty
        title = meta.get("title")
        if title is not None and str(title).strip() == "":
            errors.append(f"{md_file}: `title` is present but empty.")

    return errors


# ---------------------------------------------------------------------------
# Phase B: Validate docs/ output files
# ---------------------------------------------------------------------------


def lint_docs(docs_dir: Path) -> list[str]:
    """Validate all QMD files in docs/."""
    errors: list[str] = []
    seen_slugs: dict[str, Path] = {}

    # Check for banned folder names in docs/
    for part in BANNED_IN_DOCS:
        banned_path = docs_dir / part
        if banned_path.exists():
            errors.append(
                f"docs/ contains banned folder '{part}/'. "
                "These paths must never appear in published output."
            )

    for qmd_file in sorted(docs_dir.rglob("*.qmd")):
        try:
            text = qmd_file.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Cannot read {qmd_file}: {exc}")
            continue

        try:
            meta, body = parse(text)
        except ValueError as exc:
            errors.append(f"{qmd_file}: {exc}")
            continue

        # Check for unresolved wiki links
        wiki_errors = _check_wiki_links_in_body(body, qmd_file)
        errors.extend(wiki_errors)

        # Check for broken relative asset references
        asset_errors = _check_asset_references(body, docs_dir, qmd_file)
        errors.extend(asset_errors)

        # Slug uniqueness: derive from filename stem
        slug = qmd_file.stem
        if slug == "index":
            # index.qmd files share the slug "index" per directory — not a conflict
            slug = f"__index_{qmd_file.parent.name}"
        if slug in seen_slugs:
            errors.append(
                f"Duplicate slug '{qmd_file.stem}': "
                f"{seen_slugs[slug]} and {qmd_file}. "
                "Rename one of the files to resolve."
            )
        else:
            seen_slugs[slug] = qmd_file

    return errors


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint vault/ publishable notes and docs/ output")
    parser.add_argument(
        "--vault",
        type=Path,
        default=REPO_ROOT / "vault",
        help="Path to vault/ directory (default: repo_root/vault)",
    )
    parser.add_argument(
        "--docs",
        type=Path,
        default=REPO_ROOT,
        help="Path to publish output directory (default: repo root)",
    )
    args = parser.parse_args()

    all_errors: list[str] = []

    # Phase A
    if args.vault.is_dir():
        print(f"lint: checking vault/ publishable notes ({args.vault})")
        vault_errors = lint_vault(args.vault)
        all_errors.extend(vault_errors)
        if vault_errors:
            for e in vault_errors:
                print(f"  ERROR: {e}", file=sys.stderr)
        else:
            print("  vault/ — OK")
    else:
        print(f"WARN: vault/ not found at {args.vault} — skipping vault checks")

    # Phase B
    if args.docs.is_dir():
        print(f"lint: checking docs/ output ({args.docs})")
        docs_errors = lint_docs(args.docs)
        all_errors.extend(docs_errors)
        if docs_errors:
            for e in docs_errors:
                print(f"  ERROR: {e}", file=sys.stderr)
        else:
            print("  docs/ — OK")
    else:
        print(f"WARN: docs/ not found at {args.docs} — skipping docs checks")

    if all_errors:
        print(f"\nlint: FAILED — {len(all_errors)} error(s) found", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nlint: PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
