#!/usr/bin/env python3
"""Fetch raw Figma REST API responses."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from figma_common import dedupe, normalize_node_id, parse_figma_url, resolve_output_path, resolve_token

API_BASE = "https://api.figma.com/v1"
ASSET_REF_KEYS = {"imageRef"}
VECTOR_NODE_TYPES = {
    "VECTOR",
    "BOOLEAN_OPERATION",
    "STAR",
    "LINE",
    "ELLIPSE",
    "REGULAR_POLYGON",
}
ICON_CONTAINER_TYPES = {"FRAME", "GROUP", "COMPONENT", "INSTANCE", "COMPONENT_SET"}
ICON_NAME_PATTERN = re.compile(r"(^|[^a-z0-9])(icon|ico)([^a-z0-9]|$)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch raw Figma REST responses")
    p.add_argument("--figma-url", help="Figma URL, can include node-id")
    p.add_argument("--file-key", help="Figma file key; overrides URL parsing")
    p.add_argument("--node-id", action="append", default=[], help="Repeatable node id")
    p.add_argument("--node-ids", help="Comma-separated node ids")
    p.add_argument("--token-env", default="FIGMA_TOKEN", help="Figma token env variable")
    p.add_argument("--env-file", default=".env", help="Optional dotenv file path")
    p.add_argument(
        "--auth-mode",
        choices=["pat", "oauth", "both"],
        default="pat",
        help="Auth header mode: pat=X-Figma-Token, oauth=Authorization Bearer, both=send both headers",
    )
    p.add_argument("--depth", type=int, default=4, help="Depth for nodes extraction")
    p.add_argument("--discovery-depth", type=int, default=1, help="Depth for file discovery")
    p.add_argument("--include-geometry", action="store_true", help="Pass geometry=paths")
    p.add_argument(
        "--no-asset-urls",
        "--no-fill-image-urls",
        dest="no_fill_image_urls",
        action="store_true",
        help="Disable the supplemental /files/:key/images call for file-level image asset URLs",
    )
    p.add_argument(
        "--include-render-image-urls",
        action="store_true",
        help="Also call /images/:key to get rendered image URLs for the selected node ids",
    )
    p.add_argument("--render-format", choices=["png", "jpg", "svg", "pdf"], default="png")
    p.add_argument("--render-scale", type=float, default=2.0)
    p.add_argument(
        "--auto-svg-icon-urls",
        dest="auto_svg_icon_urls",
        action="store_true",
        help="Auto-detect vector/icon nodes in the extracted subtree and request SVG render URLs for them",
    )
    p.add_argument(
        "--no-auto-svg-icon-urls",
        dest="auto_svg_icon_urls",
        action="store_false",
        help="Disable automatic SVG render URL requests for vector/icon nodes",
    )
    p.add_argument(
        "--auto-svg-icon-limit",
        type=int,
        default=80,
        help="Maximum auto-detected vector/icon node IDs to request as SVG",
    )
    p.add_argument(
        "--inline-svg-icon-content",
        dest="inline_svg_icon_content",
        action="store_true",
        help="Download auto-detected SVG icon URLs and inline SVG XML content in the response",
    )
    p.add_argument(
        "--no-inline-svg-icon-content",
        dest="inline_svg_icon_content",
        action="store_false",
        help="Do not inline SVG XML content for auto-detected SVG icon URLs",
    )
    p.set_defaults(auto_svg_icon_urls=True, inline_svg_icon_content=True)
    p.add_argument("--plugin-data", help="Pass plugin_data query value")
    p.add_argument("--timeout", type=int, default=30)
    return p.parse_args()


def build_headers(token: str, mode: str) -> dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": "figma-raw-fetch/1.0"}
    if mode in {"pat", "both"}:
        headers["X-Figma-Token"] = token
    if mode in {"oauth", "both"}:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(url: str, headers: dict[str, str], timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 429 and attempt < 3:
                wait = e.headers.get("Retry-After", "1")
                time.sleep(max(int(wait) if wait.isdigit() else 1, 1))
                continue
            raise RuntimeError(f"Figma API {e.code}: {body}") from e
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(1)
                continue
            raise RuntimeError(f"Network error: {e}") from e
    raise RuntimeError("Request retries exhausted")


def request_supplemental_json(
    url: str,
    headers: dict[str, str],
    timeout: int,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return request_json(url, headers, timeout), None
    except RuntimeError as exc:
        return None, str(exc)


def request_text(url: str, headers: dict[str, str], timeout: int) -> str:
    req = urllib.request.Request(url, headers=headers, method="GET")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 429 and attempt < 3:
                wait = e.headers.get("Retry-After", "1")
                time.sleep(max(int(wait) if wait.isdigit() else 1, 1))
                continue
            raise RuntimeError(f"SVG fetch {e.code}: {body}") from e
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(1)
                continue
            raise RuntimeError(f"Network error: {e}") from e
    raise RuntimeError("Request retries exhausted")


def request_supplemental_text(
    url: str,
    headers: dict[str, str],
    timeout: int,
) -> tuple[str | None, str | None]:
    try:
        return request_text(url, headers, timeout), None
    except RuntimeError as exc:
        return None, str(exc)


def collect_asset_refs(value: Any, refs: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ASSET_REF_KEYS and isinstance(item, str) and item:
                refs.add(item)
                continue
            collect_asset_refs(item, refs)
        return

    if isinstance(value, list):
        for item in value:
            collect_asset_refs(item, refs)


def collect_payload_asset_refs(payload: dict[str, Any], node_ids: list[str]) -> set[str]:
    refs: set[str] = set()

    node_map = payload.get("nodes")
    if node_ids and isinstance(node_map, dict):
        for node_id in node_ids:
            entry = node_map.get(node_id)
            if not isinstance(entry, dict):
                continue
            collect_asset_refs(entry.get("document"), refs)
        return refs

    collect_asset_refs(payload.get("document"), refs)
    return refs


def filter_fill_images_payload(fill_payload: dict[str, Any], used_refs: set[str]) -> dict[str, Any]:
    if not used_refs:
        filtered = dict(fill_payload)
        meta = filtered.get("meta")
        if isinstance(meta, dict):
            filtered_meta = dict(meta)
            if isinstance(filtered_meta.get("images"), dict):
                filtered_meta["images"] = {}
                filtered["meta"] = filtered_meta
        return filtered

    meta = fill_payload.get("meta")
    if not isinstance(meta, dict):
        return fill_payload

    images = meta.get("images")
    if not isinstance(images, dict):
        return fill_payload

    filtered_images = {ref: url for ref, url in images.items() if ref in used_refs}
    filtered_meta = dict(meta)
    filtered_meta["images"] = filtered_images

    filtered = dict(fill_payload)
    filtered["meta"] = filtered_meta
    return filtered


def extract_fill_image_map(fill_payload: dict[str, Any]) -> dict[str, str]:
    meta = fill_payload.get("meta")
    if not isinstance(meta, dict):
        return {}
    images = meta.get("images")
    if not isinstance(images, dict):
        return {}
    return {str(ref): str(url) for ref, url in images.items() if isinstance(ref, str) and isinstance(url, str) and url}


def extract_render_image_map(render_payload: dict[str, Any]) -> dict[str, str]:
    images = render_payload.get("images")
    if not isinstance(images, dict):
        return {}
    return {str(node_id): str(url) for node_id, url in images.items() if isinstance(node_id, str) and isinstance(url, str) and url}


def iterate_subtree_nodes(node: Any) -> list[dict[str, Any]]:
    if not isinstance(node, dict):
        return []

    out: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = [node]
    while stack:
        current = stack.pop()
        out.append(current)
        children = current.get("children")
        if isinstance(children, list):
            for child in reversed(children):
                if isinstance(child, dict):
                    stack.append(child)
    return out


def iterate_payload_roots(payload: dict[str, Any], node_ids: list[str]) -> list[dict[str, Any]]:
    node_map = payload.get("nodes")
    if node_ids and isinstance(node_map, dict):
        roots: list[dict[str, Any]] = []
        for node_id in node_ids:
            entry = node_map.get(node_id)
            if not isinstance(entry, dict):
                continue
            document = entry.get("document")
            if isinstance(document, dict):
                roots.append(document)
        return roots

    document = payload.get("document")
    if isinstance(document, dict):
        return [document]
    return []


def looks_like_icon_name(value: str) -> bool:
    lowered = value.lower()
    if lowered.startswith("ic_") or lowered.startswith("ic-"):
        return True
    return ICON_NAME_PATTERN.search(lowered) is not None


def is_svg_icon_candidate(node: dict[str, Any]) -> bool:
    node_type = node.get("type")
    if not isinstance(node_type, str):
        return False

    if node_type in VECTOR_NODE_TYPES:
        return True

    if node_type in ICON_CONTAINER_TYPES:
        name = node.get("name")
        if isinstance(name, str) and looks_like_icon_name(name):
            return True
    return False


def collect_svg_icon_candidates(payload: dict[str, Any], node_ids: list[str]) -> list[dict[str, str]]:
    roots = iterate_payload_roots(payload, node_ids)
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    for root in roots:
        for node in iterate_subtree_nodes(root):
            if not is_svg_icon_candidate(node):
                continue
            node_id = node.get("id")
            node_type = node.get("type")
            if not isinstance(node_id, str) or not isinstance(node_type, str):
                continue
            if node_id in seen:
                continue
            seen.add(node_id)
            name = node.get("name")
            out.append(
                {
                    "id": node_id,
                    "type": node_type,
                    "name": name if isinstance(name, str) else "",
                }
            )
    return out


def build_svg_icon_assets(
    svg_nodes: list[dict[str, str]],
    svg_map: dict[str, str],
) -> list[dict[str, str]]:
    assets: list[dict[str, str]] = []
    for item in svg_nodes:
        node_id = item.get("id")
        if not node_id:
            continue
        svg_url = svg_map.get(node_id)
        if not svg_url:
            continue
        assets.append(
            {
                "id": node_id,
                "type": item.get("type", ""),
                "name": item.get("name", ""),
                "svg_url": svg_url,
            }
        )
    return assets


def fetch_svg_icon_xml_by_node_id(
    svg_nodes: list[dict[str, str]],
    svg_map: dict[str, str],
    timeout: int,
) -> tuple[dict[str, str], dict[str, str]]:
    xml_headers = {
        "Accept": "image/svg+xml,text/plain,*/*",
        "User-Agent": "figma-raw-fetch/1.0",
    }
    xml_by_node_id: dict[str, str] = {}
    errors_by_node_id: dict[str, str] = {}

    for item in svg_nodes:
        node_id = item.get("id")
        if not node_id:
            continue
        svg_url = svg_map.get(node_id)
        if not svg_url:
            continue
        svg_xml, svg_error = request_supplemental_text(svg_url, xml_headers, timeout)
        if svg_xml is not None:
            xml_by_node_id[node_id] = svg_xml
        elif svg_error:
            errors_by_node_id[node_id] = svg_error

    return xml_by_node_id, errors_by_node_id


def merge_supplemental_payload(
    payload: dict[str, Any],
    file_key: str,
    node_ids: list[str],
    headers: dict[str, str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    merged = dict(payload)
    used_refs = collect_payload_asset_refs(payload, node_ids)
    merged["_figma_used_asset_refs"] = sorted(used_refs)

    if not args.no_fill_image_urls:
        fill_url = f"{API_BASE}/files/{file_key}/images"
        fill_payload, fill_error = request_supplemental_json(fill_url, headers, args.timeout)
        if fill_payload is not None:
            filtered_fill_payload = filter_fill_images_payload(fill_payload, used_refs)
            merged["_figma_fill_images"] = filtered_fill_payload
            merged["_figma_fill_images_by_ref"] = extract_fill_image_map(filtered_fill_payload)
        elif fill_error:
            merged["_figma_fill_images_error"] = fill_error

    if node_ids and args.include_render_image_urls:
        params = {
            "ids": ",".join(node_ids),
            "format": args.render_format,
            "scale": args.render_scale,
        }
        render_url = f"{API_BASE}/images/{file_key}?" + urllib.parse.urlencode(params, safe=",")
        render_payload, render_error = request_supplemental_json(render_url, headers, args.timeout)
        if render_payload is not None:
            merged["_figma_render_images"] = render_payload
            merged["_figma_render_images_by_node_id"] = extract_render_image_map(render_payload)
        elif render_error:
            merged["_figma_render_images_error"] = render_error

    if args.auto_svg_icon_urls:
        svg_icon_nodes = collect_svg_icon_candidates(payload, node_ids)
        merged["_figma_svg_icon_nodes"] = svg_icon_nodes
        merged["_figma_svg_icon_nodes_total"] = len(svg_icon_nodes)

        max_count = max(int(args.auto_svg_icon_limit), 0)
        selected_svg_icon_nodes = svg_icon_nodes[:max_count] if max_count else []
        merged["_figma_svg_icon_nodes_selected"] = len(selected_svg_icon_nodes)
        merged["_figma_svg_icon_node_ids"] = [item["id"] for item in selected_svg_icon_nodes]

        if len(selected_svg_icon_nodes) < len(svg_icon_nodes):
            merged["_figma_svg_icon_nodes_truncated"] = True

        selected_ids = [item["id"] for item in selected_svg_icon_nodes]
        if selected_ids:
            params = {"ids": ",".join(selected_ids), "format": "svg"}
            svg_render_url = f"{API_BASE}/images/{file_key}?" + urllib.parse.urlencode(params, safe=",")
            svg_render_payload, svg_render_error = request_supplemental_json(svg_render_url, headers, args.timeout)
            if svg_render_payload is not None:
                svg_map = extract_render_image_map(svg_render_payload)
                merged["_figma_svg_icon_images"] = svg_render_payload
                merged["_figma_svg_icon_images_by_node_id"] = svg_map
                merged["_figma_svg_icon_assets"] = build_svg_icon_assets(selected_svg_icon_nodes, svg_map)
                if args.inline_svg_icon_content:
                    svg_xml_by_node_id, svg_xml_errors_by_node_id = fetch_svg_icon_xml_by_node_id(
                        selected_svg_icon_nodes,
                        svg_map,
                        args.timeout,
                    )
                    merged["_figma_svg_icon_xml_by_node_id"] = svg_xml_by_node_id
                    if svg_xml_errors_by_node_id:
                        merged["_figma_svg_icon_xml_errors_by_node_id"] = svg_xml_errors_by_node_id
            elif svg_render_error:
                merged["_figma_svg_icon_images_error"] = svg_render_error

    return merged


def main() -> int:
    args = parse_args()
    url_file, url_node_ids = (None, [])
    if args.figma_url:
        url_file, url_node_ids = parse_figma_url(args.figma_url)

    file_key = args.file_key or url_file
    if not file_key:
        print("Error: Provide --file-key or --figma-url.", file=sys.stderr)
        return 2

    node_ids: list[str] = []
    node_ids.extend(args.node_id or [])
    if args.node_ids:
        node_ids.extend([v.strip() for v in args.node_ids.split(",") if v.strip()])
    node_ids = dedupe([normalize_node_id(v) for v in (url_node_ids + node_ids)])

    token = resolve_token(args.token_env, args.env_file)
    if not token:
        print(f"Error: token not found. Set env var '{args.token_env}' or define it in '{args.env_file}'.", file=sys.stderr)
        return 2

    headers = build_headers(token, args.auth_mode)

    if node_ids:
        params = {"ids": ",".join(node_ids), "depth": args.depth}
        if args.include_geometry:
            params["geometry"] = "paths"
        if args.plugin_data:
            params["plugin_data"] = args.plugin_data
        url = f"{API_BASE}/files/{file_key}/nodes?" + urllib.parse.urlencode(params, safe=",")
    else:
        params = {"depth": args.discovery_depth}
        if args.include_geometry:
            params["geometry"] = "paths"
        if args.plugin_data:
            params["plugin_data"] = args.plugin_data
        url = f"{API_BASE}/files/{file_key}?" + urllib.parse.urlencode(params, safe=",")

    try:
        payload = request_json(url, headers, args.timeout)
    except RuntimeError as exc:
        message = str(exc)
        if "File type not supported by this endpoint" in message:
            print(
                "Error: File type not supported. Use a /design or /file URL instead of /buzz.",
                file=sys.stderr,
            )
            return 1
        print(f"Error: {message}", file=sys.stderr)
        return 1

    payload = merge_supplemental_payload(payload, file_key, node_ids, headers, args)

    out_path = resolve_output_path(
        file_key=file_key,
        node_ids=node_ids,
        payload=payload,
        suffix="-raw.json",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote raw response: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
