#!/usr/bin/env python3
"""Build compact markdown context from Figma REST API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://api.figma.com/v1"
PATH_MARKERS = {"file", "design", "proto", "board", "slides", "buzz"}
FIGJAM_TYPES = {
    "STICKY",
    "WASHI_TAPE",
    "CONNECTOR",
    "SHAPE_WITH_TEXT",
    "CODE_BLOCK",
    "STAMP",
    "WIDGET",
    "TABLE",
    "TABLE_CELL",
    "HIGHLIGHT",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract compact Figma context in markdown")
    p.add_argument("--figma-url", help="Figma URL, can contain node-id")
    p.add_argument("--file-key", help="Figma file key; overrides URL parsing")
    p.add_argument("--node-id", action="append", default=[], help="Repeatable node id")
    p.add_argument("--node-ids", help="Comma-separated node ids")
    p.add_argument("--spec-file", help="Requirement markdown path")
    p.add_argument("--output", required=True, help="Output markdown path")
    p.add_argument("--token-env", default="FIGMA_TOKEN", help="Figma token env variable")
    p.add_argument(
        "--env-file",
        default=".env",
        help="Optional dotenv file path used when token env var is not set",
    )
    p.add_argument(
        "--auth-mode",
        choices=["pat", "oauth", "both"],
        default="pat",
        help="Auth header mode: pat=X-Figma-Token, oauth=Authorization Bearer, both=send both headers",
    )
    p.add_argument("--depth", type=int, default=4, help="Depth for nodes extraction")
    p.add_argument("--discovery-depth", type=int, default=2, help="Depth when no node ids")
    p.add_argument("--max-nodes", type=int, default=320, help="Max emitted nodes")
    p.add_argument("--max-text-chars", type=int, default=280, help="Max chars per TEXT node")
    p.add_argument("--include-hidden", action="store_true", help="Keep visible=false nodes")
    p.add_argument("--include-figjam", action="store_true", help="Keep FigJam node types")
    p.add_argument("--include-geometry", action="store_true", help="Pass geometry=paths")
    p.add_argument("--plugin-data", help="Pass plugin_data query value")
    p.add_argument("--include-image-urls", action="store_true", help="Resolve node export URLs")
    p.add_argument("--image-format", choices=["png", "jpg", "svg", "pdf"], default="png")
    p.add_argument("--image-scale", type=float, default=2.0)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--stdout", action="store_true")
    return p.parse_args()


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
    parts = [p for p in parsed.path.split("/") if p]

    file_key = None
    for i, part in enumerate(parts):
        if part in PATH_MARKERS and i + 1 < len(parts):
            file_key = parts[i + 1]
            break
        if part == "community" and i + 2 < len(parts) and parts[i + 1] == "file":
            file_key = parts[i + 2]
            break

    node_ids: list[str] = []
    query = urllib.parse.parse_qs(parsed.query)
    for key in ("node-id", "node_id"):
        for value in query.get(key, []):
            node_ids.extend([v.strip() for v in value.split(",") if v.strip()])

    return file_key, [normalize_node_id(v) for v in node_ids]


def compact(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if v is None or v == "":
            continue
        if isinstance(v, dict) and not v:
            continue
        if isinstance(v, list) and not v:
            continue
        out[k] = v
    return out


def round_num(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 2)
    return value


def clamp(num: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(num, max_value))


def rgba_hex(color: dict[str, Any], opacity: float | None = None) -> str | None:
    if not isinstance(color, dict):
        return None
    r, g, b = color.get("r"), color.get("g"), color.get("b")
    if not all(isinstance(v, (int, float)) for v in (r, g, b)):
        return None
    a = color.get("a", 1.0)
    if not isinstance(a, (int, float)):
        a = 1.0
    if isinstance(opacity, (int, float)):
        a = float(a) * float(opacity)
    a = clamp(float(a), 0.0, 1.0)
    rr = int(round(clamp(float(r), 0.0, 1.0) * 255))
    gg = int(round(clamp(float(g), 0.0, 1.0) * 255))
    bb = int(round(clamp(float(b), 0.0, 1.0) * 255))
    if a >= 0.999:
        return f"#{rr:02X}{gg:02X}{bb:02X}"
    aa = int(round(a * 255))
    return f"#{rr:02X}{gg:02X}{bb:02X}{aa:02X}"


class FigmaClient:
    def __init__(self, token: str, auth_mode: str = "pat", timeout: int = 30, retries: int = 3) -> None:
        self.timeout = timeout
        self.retries = retries
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "figma-context-extractor/1.0",
        }
        if auth_mode in {"pat", "both"}:
            self.headers["X-Figma-Token"] = token
        if auth_mode in {"oauth", "both"}:
            self.headers["Authorization"] = f"Bearer {token}"

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        filtered = {k: v for k, v in params.items() if v is not None and v != ""}
        url = f"{API_BASE}{path}"
        if filtered:
            url += "?" + urllib.parse.urlencode(filtered, safe=",")

        for attempt in range(self.retries + 1):
            req = urllib.request.Request(url, headers=self.headers, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                if e.code == 429 and attempt < self.retries:
                    wait = e.headers.get("Retry-After", "1")
                    time.sleep(max(int(wait) if wait.isdigit() else 1, 1))
                    continue
                raise RuntimeError(f"Figma API {e.code}: {body}") from e
            except urllib.error.URLError as e:
                if attempt < self.retries:
                    time.sleep(1)
                    continue
                raise RuntimeError(f"Network error: {e}") from e
        raise RuntimeError("Request retries exhausted")

    def get_file(self, file_key: str, depth: int, geometry: bool, plugin_data: str | None) -> dict[str, Any]:
        params: dict[str, Any] = {"depth": depth}
        if geometry:
            params["geometry"] = "paths"
        if plugin_data:
            params["plugin_data"] = plugin_data
        return self.get(f"/files/{file_key}", params)

    def get_nodes(
        self,
        file_key: str,
        node_ids: list[str],
        depth: int,
        geometry: bool,
        plugin_data: str | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"ids": ",".join(node_ids), "depth": depth}
        if geometry:
            params["geometry"] = "paths"
        if plugin_data:
            params["plugin_data"] = plugin_data
        return self.get(f"/files/{file_key}/nodes", params)

    def get_images(self, file_key: str, node_ids: list[str], fmt: str, scale: float) -> dict[str, Any]:
        params = {"ids": ",".join(node_ids), "format": fmt, "scale": scale}
        return self.get(f"/images/{file_key}", params)


def simplify_paints(paints: list[dict[str, Any]], max_items: int = 3) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for paint in paints[:max_items]:
        item: dict[str, Any] = {
            "type": paint.get("type"),
            "visible": paint.get("visible"),
            "blendMode": paint.get("blendMode"),
            "color": rgba_hex(paint.get("color", {}), paint.get("opacity")),
            "opacity": round_num(paint.get("opacity")),
            "imageRef": paint.get("imageRef"),
        }
        stops = paint.get("gradientStops") or []
        if isinstance(stops, list) and stops:
            item["gradientStops"] = [
                compact(
                    {
                        "position": round_num(s.get("position")),
                        "color": rgba_hex(s.get("color", {})),
                    }
                )
                for s in stops[:4]
                if isinstance(s, dict)
            ]
        out.append(compact(item))
    if len(paints) > max_items:
        out.append({"_truncatedPaints": len(paints) - max_items})
    return out


def simplify_effects(effects: list[dict[str, Any]], max_items: int = 3) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for effect in effects[:max_items]:
        offset = effect.get("offset") if isinstance(effect.get("offset"), dict) else {}
        out.append(
            compact(
                {
                    "type": effect.get("type"),
                    "visible": effect.get("visible"),
                    "radius": round_num(effect.get("radius")),
                    "spread": round_num(effect.get("spread")),
                    "color": rgba_hex(effect.get("color", {})),
                    "offset": compact({"x": round_num(offset.get("x")), "y": round_num(offset.get("y"))}),
                }
            )
        )
    if len(effects) > max_items:
        out.append({"_truncatedEffects": len(effects) - max_items})
    return out

@dataclass
class State:
    max_nodes: int
    max_text_chars: int
    include_hidden: bool
    include_figjam: bool
    emitted: int = 0
    dropped_hidden: int = 0
    dropped_figjam: int = 0
    pruned: int = 0
    truncated_text: int = 0
    type_counts: Counter[str] = field(default_factory=Counter)
    style_ids: set[str] = field(default_factory=set)
    component_ids: set[str] = field(default_factory=set)


def bounds_of(node: dict[str, Any]) -> dict[str, Any]:
    b = node.get("absoluteBoundingBox")
    if not isinstance(b, dict):
        return {}
    return compact(
        {
            "x": round_num(b.get("x")),
            "y": round_num(b.get("y")),
            "width": round_num(b.get("width")),
            "height": round_num(b.get("height")),
        }
    )


def layout_of(node: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "layoutMode",
        "layoutWrap",
        "layoutSizingHorizontal",
        "layoutSizingVertical",
        "layoutPositioning",
        "layoutGrow",
        "layoutAlign",
        "primaryAxisSizingMode",
        "counterAxisSizingMode",
        "primaryAxisAlignItems",
        "counterAxisAlignItems",
        "paddingLeft",
        "paddingRight",
        "paddingTop",
        "paddingBottom",
        "itemSpacing",
        "counterAxisSpacing",
        "strokesIncludedInLayout",
        "clipsContent",
        "overflowDirection",
        "minWidth",
        "maxWidth",
        "minHeight",
        "maxHeight",
    ]
    out = {key: round_num(node.get(key)) for key in keys if key in node}
    if isinstance(node.get("constraints"), dict):
        out["constraints"] = compact(node.get("constraints", {}))
    return compact(out)


def appearance_of(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if node.get("opacity") not in (None, 1):
        out["opacity"] = round_num(node.get("opacity"))
    if node.get("blendMode") and node.get("blendMode") != "PASS_THROUGH":
        out["blendMode"] = node.get("blendMode")
    if node.get("fills"):
        out["fills"] = simplify_paints(node.get("fills", []))
    if node.get("strokes"):
        out["strokes"] = simplify_paints(node.get("strokes", []))
    if node.get("effects"):
        out["effects"] = simplify_effects(node.get("effects", []))
    for key in ("strokeWeight", "strokeAlign", "strokeJoin", "strokeCap", "cornerRadius", "rotation"):
        if key in node:
            out[key] = round_num(node.get(key))
    if node.get("rectangleCornerRadii"):
        out["rectangleCornerRadii"] = [round_num(v) for v in node.get("rectangleCornerRadii", [])]
    if node.get("isMask") is True:
        out["isMask"] = True
    return compact(out)


def text_of(node: dict[str, Any], st: State) -> dict[str, Any]:
    if node.get("type") != "TEXT":
        return {}
    chars = node.get("characters", "")
    out: dict[str, Any] = {}
    if isinstance(chars, str):
        if len(chars) > st.max_text_chars:
            out["content"] = chars[: st.max_text_chars] + "..."
            st.truncated_text += 1
        else:
            out["content"] = chars

    style = node.get("style") if isinstance(node.get("style"), dict) else {}
    keep = [
        "fontFamily",
        "fontPostScriptName",
        "fontWeight",
        "fontSize",
        "lineHeightPx",
        "lineHeightPercentFontSize",
        "letterSpacing",
        "textCase",
        "textDecoration",
        "textAlignHorizontal",
        "textAlignVertical",
        "paragraphSpacing",
        "paragraphIndent",
    ]
    out_style = {key: round_num(style.get(key)) for key in keep if key in style}
    if out_style:
        out["style"] = out_style
    if node.get("textAutoResize"):
        out["textAutoResize"] = node.get("textAutoResize")
    return compact(out)


def component_props(props: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, value in props.items():
        if not isinstance(value, dict):
            out[name] = value
            continue
        out[name] = compact(
            {
                "type": value.get("type"),
                "value": value.get("value"),
                "variantOptions": value.get("preferredValues"),
            }
        )
    return out


def track_refs(node: dict[str, Any], st: State) -> None:
    styles = node.get("styles")
    if isinstance(styles, dict):
        for value in styles.values():
            if isinstance(value, str) and value:
                st.style_ids.add(value)
    component_id = node.get("componentId")
    if isinstance(component_id, str) and component_id:
        st.component_ids.add(component_id)


def normalize(node: dict[str, Any], parent: list[str], st: State) -> dict[str, Any] | None:
    if st.emitted >= st.max_nodes:
        st.pruned += 1
        return None

    node_type = node.get("type", "UNKNOWN")
    if not st.include_hidden and node.get("visible") is False:
        st.dropped_hidden += 1
        return None
    if not st.include_figjam and node_type in FIGJAM_TYPES:
        st.dropped_figjam += 1
        return None

    name = str(node.get("name") or node_type)
    path = parent + [name]

    track_refs(node, st)
    st.emitted += 1
    st.type_counts[node_type] += 1

    out: dict[str, Any] = {
        "id": node.get("id"),
        "name": name,
        "type": node_type,
        "path": " / ".join(path),
        "visible": node.get("visible"),
        "locked": node.get("locked"),
        "styleRefs": node.get("styles"),
    }

    b = bounds_of(node)
    if b:
        out["bounds"] = b
    l = layout_of(node)
    if l:
        out["layout"] = l
    a = appearance_of(node)
    if a:
        out["appearance"] = a
    t = text_of(node, st)
    if t:
        out["text"] = t

    main_component = node.get("mainComponent") if isinstance(node.get("mainComponent"), dict) else {}
    component = compact(
        {
            "componentId": node.get("componentId"),
            "variantProperties": node.get("variantProperties"),
            "componentProperties": component_props(node.get("componentProperties", {}))
            if isinstance(node.get("componentProperties"), dict)
            else None,
            "mainComponent": compact(
                {
                    "id": main_component.get("id"),
                    "key": main_component.get("key"),
                    "name": main_component.get("name"),
                }
            ),
        }
    )
    if component:
        out["component"] = component

    children = node.get("children") if isinstance(node.get("children"), list) else []
    normalized_children: list[dict[str, Any]] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        child_out = normalize(child, path, st)
        if child_out is not None:
            normalized_children.append(child_out)
    if normalized_children:
        out["children"] = normalized_children

    return compact(out)


def merge_maps(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    merged.update(extra)
    return merged


def reference_block(styles: dict[str, Any], components: dict[str, Any], sets: dict[str, Any], st: State) -> dict[str, Any]:
    style_out: dict[str, Any] = {}
    unresolved_styles: list[str] = []
    for style_id in sorted(st.style_ids):
        style = styles.get(style_id)
        if not isinstance(style, dict):
            unresolved_styles.append(style_id)
            continue
        style_out[style_id] = compact(
            {
                "name": style.get("name"),
                "styleType": style.get("styleType"),
                "description": style.get("description"),
                "key": style.get("key"),
            }
        )

    comp_out: dict[str, Any] = {}
    unresolved_components: list[str] = []
    used_set_ids: set[str] = set()
    for comp_id in sorted(st.component_ids):
        comp = components.get(comp_id)
        if not isinstance(comp, dict):
            unresolved_components.append(comp_id)
            continue
        set_id = comp.get("componentSetId")
        if isinstance(set_id, str) and set_id:
            used_set_ids.add(set_id)
        comp_out[comp_id] = compact(
            {
                "name": comp.get("name"),
                "description": comp.get("description"),
                "key": comp.get("key"),
                "componentSetId": set_id,
            }
        )

    set_out: dict[str, Any] = {}
    unresolved_sets: list[str] = []
    for set_id in sorted(used_set_ids):
        item = sets.get(set_id)
        if not isinstance(item, dict):
            unresolved_sets.append(set_id)
            continue
        set_out[set_id] = compact(
            {
                "name": item.get("name"),
                "description": item.get("description"),
                "key": item.get("key"),
            }
        )

    return compact(
        {
            "styles": style_out,
            "components": comp_out,
            "componentSets": set_out,
            "unresolvedStyleIds": unresolved_styles,
            "unresolvedComponentIds": unresolved_components,
            "unresolvedComponentSetIds": unresolved_sets,
        }
    )


def discovery_candidates(root: dict[str, Any], max_items: int = 120) -> list[dict[str, Any]]:
    picks: list[dict[str, Any]] = []
    preferred = {"FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE", "SECTION"}

    def visit(node: dict[str, Any], lineage: list[str]) -> None:
        if len(picks) >= max_items:
            return
        ntype = node.get("type")
        name = str(node.get("name") or ntype or "")
        path = lineage + [name]
        if ntype in preferred and isinstance(node.get("id"), str):
            size = bounds_of(node)
            picks.append(
                compact(
                    {
                        "id": node.get("id"),
                        "type": ntype,
                        "name": name,
                        "path": " / ".join(path),
                        "size": compact({"width": size.get("width"), "height": size.get("height")}),
                    }
                )
            )

        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                visit(child, path)

    visit(root, [])
    return picks


def load_spec_digest(path_str: str | None, max_chars: int = 8000) -> tuple[dict[str, Any] | None, list[str]]:
    if not path_str:
        return None, []
    path = Path(path_str)
    if not path.exists():
        return None, [f"Spec file not found: {path_str}"]

    raw: str | None = None
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            raw = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    if raw is None:
        return None, [f"Unable to decode spec file: {path_str}"]

    keywords = (
        "summary",
        "scope",
        "user story",
        "acceptance",
        "scenario",
        "requirement",
        "constraint",
        "risk",
    )
    selected: list[str] = []
    for line in raw.splitlines():
        item = line.strip()
        if not item:
            continue
        lower = item.lower()
        if item.startswith("#") or item.startswith("- ") or re.match(r"^\d+\.\s", item):
            selected.append(item)
        elif any(word in lower for word in keywords):
            selected.append(item)
        if sum(len(v) for v in selected) >= max_chars:
            break

    if not selected:
        selected = [raw[:max_chars].strip()]

    digest = "\n".join(selected)
    warnings: list[str] = []
    if len(digest) > max_chars:
        digest = digest[:max_chars] + "\n..."
        warnings.append("Spec digest was truncated by max_chars.")

    return {
        "sourcePath": str(path),
        "lineCount": len(raw.splitlines()),
        "digest": digest,
    }, warnings


def summarize(st: State) -> dict[str, Any]:
    return {
        "emittedNodes": st.emitted,
        "nodeTypes": dict(st.type_counts),
        "droppedHiddenNodes": st.dropped_hidden,
        "droppedFigJamNodes": st.dropped_figjam,
        "prunedByNodeLimit": st.pruned,
        "truncatedTextNodes": st.truncated_text,
    }


def render_md(report: dict[str, Any], payload: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Figma Design Context")
    lines.append("")
    lines.append("## Source")
    lines.append(f"- Figma file key: `{report['source']['fileKey']}`")
    lines.append(f"- Mode: `{report['source']['mode']}`")
    lines.append(f"- Retrieved at (UTC): `{report['source']['retrievedAtUtc']}`")
    lines.append(f"- Endpoint: `{report['source']['endpoint']}`")
    if report["source"].get("figmaUrl"):
        lines.append(f"- Original URL: `{report['source']['figmaUrl']}`")
    if report["source"].get("selectedNodeIds"):
        node_text = ", ".join(f"`{v}`" for v in report["source"]["selectedNodeIds"])
        lines.append(f"- Selected node ids: {node_text}")
    lines.append("")

    lines.append("## Extraction Limits")
    lim = report["limits"]
    lines.append(f"- depth: `{lim['depth']}`")
    lines.append(f"- max_nodes: `{lim['maxNodes']}`")
    lines.append(f"- max_text_chars: `{lim['maxTextChars']}`")
    lines.append(f"- include_hidden: `{lim['includeHidden']}`")
    lines.append(f"- include_figjam: `{lim['includeFigJam']}`")
    lines.append("")

    if report.get("specDigest"):
        spec = report["specDigest"]
        lines.append("## Requirement Digest")
        lines.append(f"- Source: `{spec['sourcePath']}`")
        lines.append("")
        lines.append("```markdown")
        lines.append(spec["digest"])
        lines.append("```")
        lines.append("")

    lines.append("## Design Summary")
    summary = report["summary"]
    lines.append(f"- emitted_nodes: `{summary['emittedNodes']}`")
    lines.append(f"- dropped_hidden_nodes: `{summary['droppedHiddenNodes']}`")
    lines.append(f"- dropped_figjam_nodes: `{summary['droppedFigJamNodes']}`")
    lines.append(f"- pruned_by_node_limit: `{summary['prunedByNodeLimit']}`")
    lines.append(f"- truncated_text_nodes: `{summary['truncatedTextNodes']}`")
    if summary["nodeTypes"]:
        type_text = ", ".join(f"{k}:{v}" for k, v in sorted(summary["nodeTypes"].items()))
        lines.append(f"- node_types: `{type_text}`")
    lines.append("")

    if report.get("warnings"):
        lines.append("## Warnings")
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")

    if candidates:
        lines.append("## Suggested Node IDs")
        lines.append("Use these IDs in a second run to get focused component extraction.")
        lines.append("")
        lines.append("| Node ID | Type | Name | Path |")
        lines.append("| --- | --- | --- | --- |")
        for item in candidates:
            name = str(item.get("name", "")).replace("|", "\\|")
            path = str(item.get("path", "")).replace("|", "\\|")
            lines.append(f"| `{item.get('id', '')}` | `{item.get('type', '')}` | {name} | {path} |")
        lines.append("")

    lines.append("## Normalized Design JSON")
    lines.append("```json")
    lines.append(json.dumps(payload, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def resolve_inputs(args: argparse.Namespace) -> tuple[str, list[str]]:
    url_file, url_node_ids = (None, [])
    if args.figma_url:
        url_file, url_node_ids = parse_figma_url(args.figma_url)

    file_key = args.file_key or url_file
    if not file_key:
        raise ValueError("Cannot resolve file key. Provide --file-key or --figma-url.")

    node_ids: list[str] = []
    node_ids.extend(args.node_id or [])
    if args.node_ids:
        node_ids.extend([v.strip() for v in args.node_ids.split(",") if v.strip()])

    merged = [normalize_node_id(v) for v in (url_node_ids + node_ids)]
    return file_key, dedupe(merged)


def read_token_from_env_file(env_file: Path, token_env: str) -> str | None:
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
        if key.strip() != token_env:
            continue
        cleaned = value.strip().strip("'").strip('"')
        return cleaned or None
    return None


def resolve_token(token_env: str, env_file: str) -> str | None:
    env_value = os.environ.get(token_env)
    if env_value:
        return env_value

    candidate = Path(env_file)
    candidates = [candidate]
    if not candidate.is_absolute():
        candidates = [Path.cwd() / candidate]
        repo_root = Path(__file__).resolve().parents[3]
        candidates.append(repo_root / candidate)

    for path in candidates:
        token = read_token_from_env_file(path, token_env)
        if token:
            return token
    return None


def main() -> int:
    args = parse_args()

    try:
        file_key, selected = resolve_inputs(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    token = resolve_token(args.token_env, args.env_file)
    if not token:
        print(
            f"Error: token not found. Set env var '{args.token_env}' or define it in '{args.env_file}'.",
            file=sys.stderr,
        )
        return 2

    client = FigmaClient(token, auth_mode=args.auth_mode, timeout=args.timeout, retries=3)
    warnings: list[str] = []
    mode = "extraction" if selected else "discovery"
    endpoint = "GET /v1/files/:file_key/nodes" if selected else "GET /v1/files/:file_key"

    roots: list[dict[str, Any]] = []
    style_map: dict[str, Any] = {}
    comp_map: dict[str, Any] = {}
    set_map: dict[str, Any] = {}
    candidates: list[dict[str, Any]] = []

    file_name = None
    file_version = None
    file_last_modified = None

    try:
        if selected:
            meta = client.get_file(file_key, depth=1, geometry=False, plugin_data=None)
            file_name = meta.get("name")
            file_version = meta.get("version")
            file_last_modified = meta.get("lastModified")

            data = client.get_nodes(
                file_key=file_key,
                node_ids=selected,
                depth=args.depth,
                geometry=args.include_geometry,
                plugin_data=args.plugin_data,
            )
            node_map = data.get("nodes", {}) if isinstance(data.get("nodes"), dict) else {}
            for node_id in selected:
                entry = node_map.get(node_id)
                if not isinstance(entry, dict) or not isinstance(entry.get("document"), dict):
                    warnings.append(f"Node id `{node_id}` not found or inaccessible.")
                    continue
                roots.append(entry["document"])
                if isinstance(entry.get("styles"), dict):
                    style_map = merge_maps(style_map, entry.get("styles", {}))
                if isinstance(entry.get("components"), dict):
                    comp_map = merge_maps(comp_map, entry.get("components", {}))
                if isinstance(entry.get("componentSets"), dict):
                    set_map = merge_maps(set_map, entry.get("componentSets", {}))
        else:
            data = client.get_file(
                file_key=file_key,
                depth=args.discovery_depth,
                geometry=args.include_geometry,
                plugin_data=args.plugin_data,
            )
            file_name = data.get("name")
            file_version = data.get("version")
            file_last_modified = data.get("lastModified")

            if isinstance(data.get("styles"), dict):
                style_map = data.get("styles", {})
            if isinstance(data.get("components"), dict):
                comp_map = data.get("components", {})
            if isinstance(data.get("componentSets"), dict):
                set_map = data.get("componentSets", {})

            root = data.get("document")
            if not isinstance(root, dict):
                print("Error: Figma response missing `document`.", file=sys.stderr)
                return 1
            roots = [root]
            candidates = discovery_candidates(root)
            warnings.append("No node ids provided. Discovery mode only; rerun with node ids for focused output.")
    except RuntimeError as exc:
        message = str(exc)
        if "File type not supported by this endpoint" in message:
            print(
                "Error: This file type is not supported by Figma file endpoints. "
                "Use a Figma Design file URL (`/design/` or `/file/`) instead of `/buzz/`.",
                file=sys.stderr,
            )
            return 1
        print(f"Error: {message}", file=sys.stderr)
        return 1

    st = State(
        max_nodes=args.max_nodes,
        max_text_chars=args.max_text_chars,
        include_hidden=args.include_hidden,
        include_figjam=args.include_figjam,
    )
    normalized_roots: list[dict[str, Any]] = []
    for root in roots:
        out = normalize(root, [], st)
        if out is not None:
            normalized_roots.append(out)
    if not normalized_roots:
        warnings.append("No nodes were emitted after filters/limits.")

    refs = reference_block(style_map, comp_map, set_map, st)

    images = None
    if args.include_image_urls and selected:
        try:
            img_payload = client.get_images(file_key, selected, args.image_format, args.image_scale)
            images = img_payload.get("images") if isinstance(img_payload, dict) else None
        except RuntimeError as exc:
            warnings.append(f"Image URL resolution failed: {exc}")

    spec_digest, spec_warnings = load_spec_digest(args.spec_file)
    warnings.extend(spec_warnings)

    payload = compact(
        {
            "file": compact(
                {
                    "key": file_key,
                    "name": file_name,
                    "version": file_version,
                    "lastModified": file_last_modified,
                }
            ),
            "selection": {
                "requestedNodeIds": selected,
                "resolvedRoots": [n.get("id") for n in normalized_roots if n.get("id")],
            },
            "limits": {
                "maxNodes": args.max_nodes,
                "maxTextChars": args.max_text_chars,
                "includeHidden": args.include_hidden,
                "includeFigJam": args.include_figjam,
            },
            "summary": summarize(st),
            "references": refs,
            "images": images,
            "roots": normalized_roots,
        }
    )

    report = {
        "source": {
            "figmaUrl": args.figma_url,
            "fileKey": file_key,
            "selectedNodeIds": selected,
            "mode": mode,
            "endpoint": endpoint,
            "retrievedAtUtc": datetime.now(timezone.utc).isoformat(),
        },
        "limits": {
            "depth": args.depth if selected else args.discovery_depth,
            "maxNodes": args.max_nodes,
            "maxTextChars": args.max_text_chars,
            "includeHidden": args.include_hidden,
            "includeFigJam": args.include_figjam,
        },
        "summary": summarize(st),
        "warnings": warnings,
        "specDigest": spec_digest,
    }

    markdown = render_md(report, payload, candidates)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    if args.stdout:
        print(markdown)
    print(f"Wrote markdown context: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
