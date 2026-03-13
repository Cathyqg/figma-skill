#!/usr/bin/env python3
"""Shared helpers for Figma extractor scripts."""

from __future__ import annotations

import os
import re
import urllib.parse
from pathlib import Path
from typing import Any

PATH_MARKERS = {"file", "design", "proto", "board", "slides", "buzz"}
FIXED_OUTPUT_DIR = Path("spec/figma")


def normalize_node_id(value: str) -> str:
    raw = urllib.parse.unquote(value.strip())
    if re.fullmatch(r"\d+-\d+", raw):
        left, right = raw.split("-", 1)
        return f"{left}:{right}"
    return raw


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def parse_figma_url(url: str) -> tuple[str | None, list[str]]:
    parsed = urllib.parse.urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]

    file_key = None
    branch_key = None
    for index, part in enumerate(parts):
        if part in PATH_MARKERS and index + 1 < len(parts):
            file_key = parts[index + 1]
            break
        if part == "community" and index + 2 < len(parts) and parts[index + 1] == "file":
            file_key = parts[index + 2]
            break
        if part == "branch" and index + 1 < len(parts):
            branch_key = parts[index + 1]

    node_ids: list[str] = []
    query = urllib.parse.parse_qs(parsed.query)
    for key in ("node-id", "node_id"):
        for value in query.get(key, []):
            node_ids.extend([item.strip() for item in value.split(",") if item.strip()])

    return branch_key or file_key, [normalize_node_id(value) for value in node_ids]


def read_env_value_from_file(env_file: Path, env_name: str) -> str | None:
    if not env_file.exists():
        return None
    try:
        lines = env_file.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return None

    for line in lines:
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        if item.startswith("export "):
            item = item[len("export ") :].strip()
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key.strip() != env_name:
            continue
        cleaned = value.strip().strip("'").strip('"')
        return cleaned or None
    return None


def resolve_env_value(env_name: str, env_file: str) -> str | None:
    env_value = os.environ.get(env_name)
    if env_value:
        return env_value

    candidate = Path(env_file)
    candidates = [candidate]
    if not candidate.is_absolute():
        candidates = [Path.cwd() / candidate]
        script_path = Path(__file__).resolve()
        skill_root = script_path.parent.parent
        candidates.append(skill_root / candidate)

        skills_dir = skill_root.parent
        if skills_dir.name == "skills":
            candidates.append(skills_dir.parent / candidate)

    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        value = read_env_value_from_file(path, env_name)
        if value:
            return value
    return None


def resolve_token(token_env: str, env_file: str) -> str | None:
    return resolve_env_value(token_env, env_file)


def slugify_filename(value: str, default: str = "figma") -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", " ", value.strip())
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = cleaned.strip("._-").lower()
    return cleaned or default


def select_output_label(payload: dict[str, Any], node_ids: list[str]) -> str | None:
    node_map = payload.get("nodes")
    if node_ids and isinstance(node_map, dict):
        for node_id in node_ids:
            entry = node_map.get(node_id)
            if not isinstance(entry, dict):
                continue
            document = entry.get("document")
            if not isinstance(document, dict):
                continue
            name = document.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()

    document = payload.get("document")
    if isinstance(document, dict):
        name = document.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()

    name = payload.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()

    return None


def build_output_stem(file_key: str, node_ids: list[str], payload: dict[str, Any]) -> str:
    label = select_output_label(payload, node_ids) or file_key
    stem = slugify_filename(label, default="figma")

    if node_ids:
        node_suffix = slugify_filename(normalize_node_id(node_ids[0]).replace(":", "-"), default="node")
        if node_suffix not in stem:
            stem = f"{stem}-{node_suffix}"
        if len(node_ids) > 1:
            stem = f"{stem}-plus-{len(node_ids) - 1}"
    else:
        key_suffix = slugify_filename(file_key[:8], default="file")
        if key_suffix and key_suffix not in stem:
            stem = f"{stem}-{key_suffix}"

    return stem


def resolve_output_path(
    file_key: str,
    node_ids: list[str],
    payload: dict[str, Any],
    suffix: str,
) -> Path:
    filename = f"{build_output_stem(file_key, node_ids, payload)}{suffix}"
    return FIXED_OUTPUT_DIR / filename
