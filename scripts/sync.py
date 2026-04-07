#!/usr/bin/env python3
"""
sync.py — Vault to Docs Synchronization
========================================
Reads vault/ notes with `publish: true` and converts them to publishable
QMD files in docs/.

Usage:
    python scripts/sync.py [--vault VAULT_DIR] [--docs DOCS_DIR] [--dry-run]

Exit codes:
    0  All publishable notes synced successfully.
    1  Hard failure: ambiguous links, missing required fields, or unknown category.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Allow running as `python scripts/sync.py` from repo root
sys.path.insert(0, str(Path(__file__).parent))
from utils.frontmatter import derive_slug, dump, parse

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

CATEGORY_MAP: dict[str, str] = {
    "architecture": "architecture",
    "guides": "guides",
    "references": "references",
    "decisions": "decisions",
    "reports": "reports",
}

# vault/ sub-directories that are NEVER published, even if a note has publish: true
NEVER_PUBLISH_DIRS: set[str] = {"inbox", "daily"}

# Obsidian image/asset extensions
ASSET_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".pdf", ".mp4", ".mov"}
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class VaultNote:
    source_path: Path
    meta: dict
    body: str
    # Computed after indexing
    output_path: Path | None = None


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


def index_vault(vault_dir: Path) -> tuple[dict[str, list[VaultNote]], list[str]]:
    """Walk vault/ and build a title → [VaultNote] index.

    Returns (title_index, errors).
    """
    title_index: dict[str, list[VaultNote]] = {}
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

        # Determine title: frontmatter title > filename stem
        title = str(meta.get("title") or md_file.stem)

        note = VaultNote(source_path=md_file, meta=meta, body=body)
        title_index.setdefault(title, []).append(note)

    return title_index, errors


# ---------------------------------------------------------------------------
# Wiki link conversion
# ---------------------------------------------------------------------------

# Matches [[Target]] and [[Target|display text]]
_WIKI_LINK_RE = re.compile(r"\[\[([^\[\]|]+?)(?:\|([^\[\]]+?))?\]\]")

# Matches ![[target]] — Obsidian embeds
_EMBED_RE = re.compile(r"!\[\[([^\[\]]+?)\]\]")


def _resolve_wiki_link(
    target: str,
    title_index: dict[str, list[VaultNote]],
    output_path: Path,
    docs_dir: Path,
) -> str | None:
    """Return the relative path string for a wiki link target, or None if unresolvable."""
    candidates = title_index.get(target)
    if not candidates:
        return None

    # Filter to only notes that have an output_path (i.e., publishable)
    published = [n for n in candidates if n.output_path is not None]
    if not published:
        return None

    target_output = published[0].output_path
    rel = Path(target_output).relative_to(docs_dir)
    from_dir = output_path.parent
    # Compute relative path from the output file's directory to the target
    rel_path = _relative_path(from_dir, target_output)
    return rel_path


def _relative_path(from_dir: Path, to_file: Path) -> str:
    """Compute a POSIX-style relative path from from_dir to to_file."""
    try:
        rel = to_file.relative_to(from_dir)
        return rel.as_posix()
    except ValueError:
        # Different subtree — walk up
        parts_from = from_dir.parts
        parts_to = to_file.parts
        # Find common prefix length
        common = 0
        for a, b in zip(parts_from, parts_to):
            if a == b:
                common += 1
            else:
                break
        ups = len(parts_from) - common
        down = parts_to[common:]
        rel = "/".join([".."] * ups + list(down))
        return rel


def _process_body(
    body: str,
    title_index: dict[str, list[VaultNote]],
    output_path: Path,
    docs_dir: Path,
    source_path: Path,
) -> tuple[str, list[str], list[str]]:
    """Convert wiki links in body text, respecting fenced code blocks.

    Returns (converted_body, warnings, errors).
    - warnings: non-fatal issues (unresolvable links, embeds)
    - errors: fatal issues (ambiguous links pointing to multiple published notes)
    """
    warnings: list[str] = []
    errors: list[str] = []
    lines = body.split("\n")
    result: list[str] = []
    in_fence = False
    fence_marker: str | None = None

    for line in lines:
        stripped = line.strip()

        if not in_fence:
            # Detect opening fence
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = True
                fence_marker = stripped[:3]
                result.append(line)
                continue
        else:
            # Detect closing fence (same marker, nothing else meaningful on line)
            if fence_marker and stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = None
            result.append(line)
            continue

        # --- Process line outside code fence ---

        # Handle embeds first (![[...]]) before wiki links
        def replace_embed(m: re.Match) -> str:
            embed_target = m.group(1).strip()
            ext = Path(embed_target).suffix.lower()
            if ext in ASSET_EXTENSIONS:
                # Image embed → convert to markdown image referencing docs/assets/
                asset_rel = f"../assets/{embed_target}"
                warnings.append(
                    f"{source_path.name}: image embed '![[{embed_target}]]' "
                    f"converted to '![{embed_target}]({asset_rel})'. "
                    "Ensure the asset exists in vault/assets/."
                )
                return f"![{embed_target}]({asset_rel})"
            else:
                warnings.append(
                    f"{source_path.name}: note embed '![[{embed_target}]]' "
                    "cannot be rendered in Quarto — replaced with a comment. "
                    "Resolve manually or remove before publishing."
                )
                return f"<!-- EMBED: {embed_target} (not rendered in published output) -->"

        line = _EMBED_RE.sub(replace_embed, line)

        # Handle [[wiki links]]
        def replace_wiki(m: re.Match) -> str:
            target = m.group(1).strip()
            display = (m.group(2) or "").strip() or target

            candidates = title_index.get(target)
            if not candidates:
                warnings.append(
                    f"{source_path.name}: [[{target}]] — no note found with this title. "
                    "Link left as plain text."
                )
                return display

            published = [n for n in candidates if n.output_path is not None]

            if len(published) > 1:
                paths = ", ".join(str(n.source_path) for n in published)
                errors.append(
                    f"{source_path.name}: [[{target}]] is ambiguous — "
                    f"matches {len(published)} published notes: {paths}. "
                    "Give each note a unique title or use a slug alias."
                )
                return display  # placeholder; sync will fail anyway

            if len(published) == 0:
                warnings.append(
                    f"{source_path.name}: [[{target}]] — note exists but is not published "
                    "(publish: true not set or in a never-publish directory). "
                    "Link rendered as plain text."
                )
                return display

            rel = _relative_path(output_path.parent, published[0].output_path)
            return f"[{display}]({rel})"

        line = _WIKI_LINK_RE.sub(replace_wiki, line)
        result.append(line)

    return "\n".join(result), warnings, errors


# ---------------------------------------------------------------------------
# Asset copying
# ---------------------------------------------------------------------------


def _copy_referenced_assets(
    body: str, vault_assets_dir: Path, docs_assets_dir: Path, source_name: str
) -> list[str]:
    """Copy assets referenced via markdown image syntax into docs/assets/.

    Returns list of warning strings for missing assets.
    """
    warnings: list[str] = []
    # Match ![alt](path) where path points to vault/assets or just a bare filename
    image_re = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    for m in image_re.finditer(body):
        href = m.group(1).strip()
        if href.startswith("http://") or href.startswith("https://"):
            continue
        # Resolve relative to vault/assets/ for bare filenames
        filename = Path(href).name
        src = vault_assets_dir / filename
        dst = docs_assets_dir / filename
        if src.exists():
            docs_assets_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        else:
            warnings.append(
                f"{source_name}: referenced asset '{filename}' not found in vault/assets/. "
                "Add it there or update the link."
            )
    return warnings


# ---------------------------------------------------------------------------
# Output path resolution
# ---------------------------------------------------------------------------


def _output_path_for(note: VaultNote, docs_dir: Path) -> tuple[Path | None, str | None]:
    """Determine the docs/ output path for a publishable note.

    Returns (output_path, error_message). error_message is None on success.
    """
    meta = note.meta
    category = str(meta.get("category", "")).strip()
    if category not in CATEGORY_MAP:
        return None, (
            f"{note.source_path}: unknown category '{category}'. "
            f"Allowed values: {sorted(CATEGORY_MAP.keys())}"
        )
    slug = str(meta.get("slug", "")).strip()
    if not slug:
        slug = derive_slug(str(meta.get("title", note.source_path.stem)))
    folder = CATEGORY_MAP[category]
    return docs_dir / folder / f"{slug}.qmd", None


# ---------------------------------------------------------------------------
# Main sync logic
# ---------------------------------------------------------------------------


def sync(vault_dir: Path, docs_dir: Path, dry_run: bool = False) -> int:
    """Run the full sync pipeline. Returns exit code (0 = success, 1 = failure)."""
    print(f"sync: vault={vault_dir}  docs={docs_dir}  dry_run={dry_run}")

    # --- Step 1: Index all vault notes ---
    title_index, index_errors = index_vault(vault_dir)
    if index_errors:
        for e in index_errors:
            print(f"  ERROR (index): {e}", file=sys.stderr)
        return 1

    total_notes = sum(len(v) for v in title_index.values())
    print(f"  Indexed {total_notes} notes from vault/")

    # --- Step 2: Identify publishable notes and assign output paths ---
    publishable: list[VaultNote] = []
    hard_errors: list[str] = []

    for notes in title_index.values():
        for note in notes:
            # Skip never-publish directories
            try:
                rel_parts = note.source_path.relative_to(vault_dir).parts
            except ValueError:
                rel_parts = ()
            if rel_parts and rel_parts[0] in NEVER_PUBLISH_DIRS:
                continue

            if note.meta.get("publish") is not True:
                continue

            # Validate required fields
            missing = [f for f in REQUIRED_PUBLISH_FIELDS if f not in note.meta]
            if missing:
                hard_errors.append(
                    f"{note.source_path}: publish: true but missing required fields: "
                    + ", ".join(missing)
                )
                continue

            out_path, err = _output_path_for(note, docs_dir)
            if err:
                hard_errors.append(err)
                continue

            note.output_path = out_path
            publishable.append(note)

    if hard_errors:
        for e in hard_errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        return 1

    print(f"  Found {len(publishable)} publishable notes")

    # --- Step 3: Check for duplicate output paths ---
    seen_outputs: dict[Path, VaultNote] = {}
    for note in publishable:
        assert note.output_path is not None
        if note.output_path in seen_outputs:
            prev = seen_outputs[note.output_path]
            hard_errors.append(
                f"Duplicate output path {note.output_path}:\n"
                f"  {prev.source_path}\n"
                f"  {note.source_path}\n"
                "Assign unique slugs to resolve this."
            )
        else:
            seen_outputs[note.output_path] = note

    if hard_errors:
        for e in hard_errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        return 1

    # --- Step 4: Convert and write each note ---
    vault_assets = vault_dir / "assets"
    docs_assets = docs_dir / "assets"
    all_warnings: list[str] = []
    convert_errors: list[str] = []

    for note in publishable:
        assert note.output_path is not None
        converted_body, warnings, errors = _process_body(
            note.body, title_index, note.output_path, docs_dir, note.source_path
        )
        all_warnings.extend(warnings)
        convert_errors.extend(errors)

        if errors:
            # Don't write this note — it has ambiguous links
            continue

        # Copy assets referenced in the converted body
        asset_warnings = _copy_referenced_assets(
            converted_body, vault_assets, docs_assets, note.source_path.name
        )
        all_warnings.extend(asset_warnings)

        # Build publish-safe frontmatter (keep only fields Quarto cares about)
        pub_meta: dict = {
            "title": note.meta["title"],
        }
        if "summary" in note.meta:
            pub_meta["description"] = note.meta["summary"]
        if "tags" in note.meta:
            pub_meta["categories"] = note.meta["tags"]
        if "updated" in note.meta:
            pub_meta["date"] = str(note.meta["updated"])

        output_text = dump(pub_meta, converted_body)

        if dry_run:
            print(f"  [dry-run] would write → {note.output_path}")
        else:
            note.output_path.parent.mkdir(parents=True, exist_ok=True)
            note.output_path.write_text(output_text, encoding="utf-8")
            print(f"  wrote → {note.output_path.relative_to(REPO_ROOT)}")

    if convert_errors:
        for e in convert_errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        return 1

    if all_warnings:
        print(f"\n  {len(all_warnings)} warning(s):")
        for w in all_warnings:
            print(f"  WARN: {w}")

    written = len(publishable) - len(convert_errors)
    print(f"\nsync: complete — {written} notes written, {len(all_warnings)} warnings")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync vault/ notes to docs/")
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without writing anything",
    )
    args = parser.parse_args()

    if not args.vault.is_dir():
        print(f"ERROR: vault directory not found: {args.vault}", file=sys.stderr)
        sys.exit(1)
    if not args.docs.is_dir():
        print(f"ERROR: docs directory not found: {args.docs}", file=sys.stderr)
        sys.exit(1)

    sys.exit(sync(args.vault, args.docs, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
