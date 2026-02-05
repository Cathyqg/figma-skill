#!/usr/bin/env python3
"""Fetch raw Figma REST API responses for testing."""

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
from pathlib import Path
from typing import Any

API_BASE = "https://api.figma.com/v1"
PATH_MARKERS = {"file", "design", "proto", "board", "slides", "buzz"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch raw Figma REST responses (test-only)")
    p.add_argument("--figma-url", help="Figma URL, can include node-id")
    p.add_argument("--file-key", help="Figma file key; overrides URL parsing")
    p.add_argument("--node-id", action="append", default=[], help="Repeatable node id")
    p.add_argument("--node-ids", help="Comma-separated node ids")
    p.add_argument("--output", required=True, help="Output JSON path")
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
    p.add_argument("--plugin-data", help="Pass plugin_data query value")
    p.add_argument("--timeout", type=int, default=30)
    return p.parse_args()


def normalize_node_id(value: str) -> str:
    raw = urllib.parse.unquote(value.strip())
    if re.fullmatch(r"\d+-\d+", raw):
        left, right = raw.split("-", 1)
        return f"{left}:{right}"
    return raw


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


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


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
    raise RuntimeError("Request retries exhausted")


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

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote raw response: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
