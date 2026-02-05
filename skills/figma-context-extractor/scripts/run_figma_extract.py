#!/usr/bin/env python3
"""One-shot helper: fetch raw Figma JSON + parsed markdown."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RAW_SCRIPT = SCRIPT_DIR / "fetch_figma_raw.py"
PARSE_SCRIPT = SCRIPT_DIR / "build_figma_context.py"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch raw Figma JSON and parsed markdown in one run")
    p.add_argument("--figma-url", help="Figma URL, can include node-id")
    p.add_argument("--file-key", help="Figma file key; overrides URL parsing")
    p.add_argument("--node-id", action="append", default=[], help="Repeatable node id")
    p.add_argument("--node-ids", help="Comma-separated node ids")
    p.add_argument("--spec-file", help="Requirement markdown path (optional)")
    p.add_argument("--output-dir", default="tmp", help="Output directory")
    p.add_argument("--raw-name", default="figma-raw.json", help="Raw JSON filename")
    p.add_argument("--parsed-name", default="figma-context.md", help="Parsed markdown filename")
    p.add_argument("--token-env", default="FIGMA_TOKEN", help="Figma token env variable")
    p.add_argument("--env-file", default=".env", help="Optional dotenv file path")
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
    p.add_argument("--timeout", type=int, default=30)
    return p.parse_args()


def build_common_args(args: argparse.Namespace) -> list[str]:
    parts: list[str] = []
    if args.figma_url:
        parts += ["--figma-url", args.figma_url]
    if args.file_key:
        parts += ["--file-key", args.file_key]
    for node_id in args.node_id or []:
        parts += ["--node-id", node_id]
    if args.node_ids:
        parts += ["--node-ids", args.node_ids]
    parts += ["--token-env", args.token_env, "--env-file", args.env_file, "--auth-mode", args.auth_mode]
    parts += ["--depth", str(args.depth), "--discovery-depth", str(args.discovery_depth)]
    if args.include_geometry:
        parts.append("--include-geometry")
    if args.plugin_data:
        parts += ["--plugin-data", args.plugin_data]
    return parts


def run_command(cmd: list[str]) -> None:
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = out_dir / args.raw_name
    parsed_path = out_dir / args.parsed_name

    common = build_common_args(args)

    raw_cmd = [sys.executable, str(RAW_SCRIPT), *common, "--output", str(raw_path)]
    run_command(raw_cmd)

    parsed_cmd = [
        sys.executable,
        str(PARSE_SCRIPT),
        *common,
        "--output",
        str(parsed_path),
        "--max-nodes",
        str(args.max_nodes),
        "--max-text-chars",
        str(args.max_text_chars),
    ]
    if args.include_hidden:
        parsed_cmd.append("--include-hidden")
    if args.include_figjam:
        parsed_cmd.append("--include-figjam")
    if args.spec_file:
        parsed_cmd += ["--spec-file", args.spec_file]

    run_command(parsed_cmd)
    print(f"Wrote raw: {raw_path}")
    print(f"Wrote parsed: {parsed_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
