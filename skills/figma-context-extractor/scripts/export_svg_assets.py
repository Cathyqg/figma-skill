#!/usr/bin/env python3
"""Export normalized SVG cache files and hash manifest from extractor raw JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

RAW_SUFFIX = "-raw.json"
MANIFEST_SUFFIX = "-svg-manifest.json"
TAG_GAP_PATTERN = re.compile(r">\s+<")
MULTI_BLANK_LINE_PATTERN = re.compile(r"\n{2,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SVG hash manifest from extractor raw JSON")
    parser.add_argument(
        "--raw-json",
        required=True,
        help="Path to extractor raw JSON artifact (usually under spec/figma)",
    )
    parser.add_argument(
        "--svg-cache-dir",
        default="spec/figma/assets/svg",
        help="Directory for hash-named cached SVG files",
    )
    parser.add_argument(
        "--manifest-path",
        help="Optional explicit output path for the manifest JSON file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite cached SVG files when hash file already exists",
    )
    return parser.parse_args()


def normalize_svg_xml(svg_xml: str) -> str:
    """Normalize SVG XML with a conservative, deterministic strategy."""
    normalized = svg_xml.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = TAG_GAP_PATTERN.sub("><", normalized)
    normalized = MULTI_BLANK_LINE_PATTERN.sub("\n", normalized)
    return normalized


def safe_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def display_path(path: Path, base_dir: Path) -> str:
    try:
        return path.resolve().relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def infer_manifest_path(raw_json_path: Path) -> Path:
    file_name = raw_json_path.name
    stem = file_name[: -len(RAW_SUFFIX)] if file_name.endswith(RAW_SUFFIX) else raw_json_path.stem
    return raw_json_path.with_name(f"{stem}{MANIFEST_SUFFIX}")


def load_payload(raw_json_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(raw_json_path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise RuntimeError(f"Unable to read raw JSON file: {raw_json_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Raw JSON parse failed: {raw_json_path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Raw JSON root must be an object.")
    return payload


def extract_svg_xml_by_node_id(payload: dict[str, Any]) -> dict[str, str]:
    raw_map = payload.get("_figma_svg_icon_xml_by_node_id")
    if not isinstance(raw_map, dict):
        return {}

    out: dict[str, str] = {}
    for node_id, svg_xml in raw_map.items():
        if isinstance(node_id, str) and node_id and isinstance(svg_xml, str) and svg_xml.strip():
            out[node_id] = svg_xml
    return out


def extract_svg_meta_by_node_id(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    raw_assets = payload.get("_figma_svg_icon_assets")
    if not isinstance(raw_assets, list):
        return {}

    out: dict[str, dict[str, str]] = {}
    for item in raw_assets:
        if not isinstance(item, dict):
            continue
        node_id = item.get("id")
        if not isinstance(node_id, str) or not node_id:
            continue
        out[node_id] = {
            "type": safe_str(item.get("type")),
            "name": safe_str(item.get("name")),
            "svg_url": safe_str(item.get("svg_url")),
        }
    return out


def build_manifest(
    raw_json_path: Path,
    svg_cache_dir: Path,
    payload: dict[str, Any],
    overwrite: bool,
    base_dir: Path,
) -> dict[str, Any]:
    svg_xml_by_node_id = extract_svg_xml_by_node_id(payload)
    svg_meta_by_node_id = extract_svg_meta_by_node_id(payload)

    assets: list[dict[str, str]] = []
    written_count = 0
    reused_count = 0

    for node_id in sorted(svg_xml_by_node_id):
        normalized_svg = normalize_svg_xml(svg_xml_by_node_id[node_id])
        if not normalized_svg:
            continue

        svg_hash = hashlib.sha256(normalized_svg.encode("utf-8")).hexdigest()
        cached_svg_file = svg_cache_dir / f"{svg_hash}.svg"

        if cached_svg_file.exists() and not overwrite:
            reused_count += 1
        else:
            cached_svg_file.write_text(normalized_svg, encoding="utf-8")
            written_count += 1

        meta = svg_meta_by_node_id.get(node_id, {})
        assets.append(
            {
                "node_id": node_id,
                "type": safe_str(meta.get("type")),
                "name": safe_str(meta.get("name")),
                "svg_url": safe_str(meta.get("svg_url")),
                "svg_hash": svg_hash,
                "cached_svg_path": display_path(cached_svg_file, base_dir),
            }
        )

    return {
        "source_raw_json": display_path(raw_json_path, base_dir),
        "source_name": safe_str(payload.get("name")),
        "source_version": safe_str(payload.get("version")),
        "svg_cache_dir": display_path(svg_cache_dir, base_dir),
        "asset_count": len(assets),
        "written_count": written_count,
        "reused_count": reused_count,
        "assets": assets,
    }


def main() -> int:
    args = parse_args()
    base_dir = Path.cwd()

    raw_json_path = Path(args.raw_json)
    if not raw_json_path.exists():
        print(f"Error: raw JSON file not found: {raw_json_path}", file=sys.stderr)
        return 2

    svg_cache_dir = Path(args.svg_cache_dir)
    manifest_path = Path(args.manifest_path) if args.manifest_path else infer_manifest_path(raw_json_path)

    try:
        payload = load_payload(raw_json_path)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        svg_cache_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"Error: unable to create output directories: {exc}", file=sys.stderr)
        return 1

    try:
        manifest = build_manifest(raw_json_path, svg_cache_dir, payload, args.overwrite, base_dir)
    except OSError as exc:
        print(f"Error: unable to write cached SVG file: {exc}", file=sys.stderr)
        return 1

    try:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"Error: unable to write manifest file: {exc}", file=sys.stderr)
        return 1

    if manifest["asset_count"] == 0:
        print(
            "Warning: no SVG XML entries found in '_figma_svg_icon_xml_by_node_id'; wrote an empty manifest.",
            file=sys.stderr,
        )

    print(f"Wrote SVG manifest: {manifest_path}")
    print(
        "SVG assets: total={total}, wrote={wrote}, reused={reused}".format(
            total=manifest["asset_count"],
            wrote=manifest["written_count"],
            reused=manifest["reused_count"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
