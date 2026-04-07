"""Frontmatter parsing utilities shared by sync.py and lint.py."""

from __future__ import annotations

import re
from typing import Any

import yaml


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Parse a markdown/QMD file with YAML frontmatter.

    Returns (meta, body) where meta is the parsed frontmatter dict
    and body is the remaining content after the closing --- delimiter.

    If no frontmatter is found, returns ({}, original_text).
    Raises ValueError on malformed YAML.
    """
    if not text.startswith("---"):
        return {}, text

    # Find the closing ---  (must be on its own line)
    rest = text[3:]
    close = re.search(r"^\-{3,}\s*$", rest, re.MULTILINE)
    if close is None:
        return {}, text

    yaml_text = rest[: close.start()].strip()
    body = rest[close.end() :].lstrip("\n")

    try:
        meta = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML frontmatter: {exc}") from exc

    if not isinstance(meta, dict):
        raise ValueError("Frontmatter must be a YAML mapping, not a scalar or list.")

    return meta, body


def dump(meta: dict[str, Any], body: str) -> str:
    """Serialize frontmatter dict and body back to a markdown string."""
    yaml_text = yaml.dump(
        meta,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip()
    return f"---\n{yaml_text}\n---\n\n{body}"


def derive_slug(title: str) -> str:
    """Derive a deterministic kebab-case slug from a title string.

    Rules:
    - Lowercase
    - Non-alphanumeric characters replaced by hyphens
    - Consecutive hyphens collapsed
    - Leading/trailing hyphens stripped
    """
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug
