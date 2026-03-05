---
name: figma-context-extractor
description: Fetch raw Figma REST data for downstream UI implementation. Use when a user provides a Figma URL or node ids and needs stable JSON artifacts (including image asset URLs and auto-detected SVG icon URLs by default) before component coding, with default SVG hash manifest generation for downstream asset dedupe.
---

# Figma Context Extractor

## Goal

Produce a stable raw JSON artifact from official Figma REST endpoints. Keep script-side processing minimal and deterministic.

## Required Inputs

- `figma_url` or `file_key` (required)
  - Branch URLs are supported. If `/branch/<BRANCH_KEY>` exists, use branch key first.
- `FIGMA_TOKEN` (required by default)
- `node_id` list (recommended for node-scoped extraction)
- `auth_mode` (optional, default `pat`)
- `env_file` (optional, default `.env`)

## CLI Parameter Catalog

### Target Selection

- `--figma-url`
  - Parse file key and optional `node-id` from URL.
- `--file-key`
  - Override file key parsed from URL.
- `--node-id`
  - Repeatable node id input.
- `--node-ids`
  - Comma-separated node ids.

### Output

- Output directory is fixed to `spec/figma`.
- Do not pass output path arguments.
- Do not configure output directory via environment variables.

### Auth and Environment

- `--token-env` (default `FIGMA_TOKEN`)
- `--env-file` (default `.env`)
- `--auth-mode` (default `pat`)
  - `pat`: `X-Figma-Token`
  - `oauth`: `Authorization: Bearer`
  - `both`: send both headers

### Payload Size and Fidelity

- `--depth` (default `4`)
  - Used by `GET /v1/files/:file_key/nodes`.
- `--discovery-depth` (default `1`)
  - Used by `GET /v1/files/:file_key` when node ids are absent.
- `--include-geometry` (default off)
  - Adds `geometry=paths`. Use only when vector path fidelity is required.
- `--plugin-data` (default unset)
  - Include plugin payload only when needed.

### Supplemental Images

- `--no-asset-urls` (alias: `--no-fill-image-urls`)
  - Disable `GET /v1/files/:file_key/images`.
- `--include-render-image-urls`
  - Enable `GET /v1/images/:file_key` for selected node ids.
- `--render-format` (default `png`)
- `--render-scale` (default `2.0`)
- `--auto-svg-icon-urls` / `--no-auto-svg-icon-urls` (default on)
  - Auto-detect vector/icon-like nodes from returned subtree and request `format=svg` render URLs.
- `--auto-svg-icon-limit` (default `80`)
  - Max auto-detected node ids requested in one SVG render call.
- `--inline-svg-icon-content` / `--no-inline-svg-icon-content` (default on)
  - Download auto-detected SVG icon URLs and inline SVG XML content into the raw response.

### SVG Manifest Export (Default On)

- `--export-svg-manifest`
  - Explicitly enable hash-based SVG cache files and a `*-svg-manifest.json` file after writing raw JSON.
- `--no-export-svg-manifest`
  - Disable hash-based SVG cache and manifest generation for this run.
- `--svg-cache-dir` (default `spec/figma/assets/svg`)
  - Cache directory for hash-named SVG files.
- `--svg-manifest-path` (default inferred from raw filename)
  - Optional explicit output path for manifest JSON.
- `--overwrite-svg-cache` (default off)
  - Overwrite existing hash SVG files in cache directory.

### Network

- `--timeout` (default `30` seconds)

## Escalation Rules

Start with the smallest payload that can answer the task. Re-run only when the current result is insufficient.

- Symptom: target children are missing
  - Action: increase `--depth` (`4 -> 8 -> 12`)
- Symptom: no node id yet
  - Action: run discovery with `--discovery-depth 1`; increase only if too shallow
- Symptom: vector path details are missing for icons/logos
  - Action: add `--include-geometry`
- Symptom: need node preview/export image
  - Action: add `--include-render-image-urls`
- Symptom: plugin metadata is required
  - Action: add `--plugin-data <value>`
- Symptom: payload too large and image assets are irrelevant
  - Action: add `--no-asset-urls`

## Workflow

0. Resolve installed skill directory before invoking scripts.
   - Do not assume project-relative `skills/figma-context-extractor/`.
   - In Codex, locate this `SKILL.md` and use sibling `scripts/`.
   - In OpenCode, probe these paths and use first match:
     - `.opencode/skills/figma-context-extractor`
     - `~/.config/opencode/skills/figma-context-extractor`
     - `.agents/skills/figma-context-extractor`
     - `~/.agents/skills/figma-context-extractor`
     - `.claude/skills/figma-context-extractor`
     - `~/.claude/skills/figma-context-extractor`
1. Resolve `file_key` and node ids from URL/flags.
2. Run `GET /v1/files/:file_key/nodes` when node ids exist; otherwise run `GET /v1/files/:file_key`.
3. By default run `GET /v1/files/:file_key/images`, then keep only image refs used in current payload.
4. By default, auto-detect vector/icon-like nodes and run `GET /v1/images/:file_key` with `format=svg` for those node ids.
5. Only when requested, additionally run `GET /v1/images/:file_key` for explicit node render URLs (`--include-render-image-urls`).
6. Write one stable raw JSON file under `spec/figma/` and return raw JSON only.
7. By default, generate normalized SVG hash artifacts for downstream asset reuse.
8. Only when needed, disable default manifest export with `--no-export-svg-manifest`.
9. Optional fallback: run `<skill-dir>/scripts/export_svg_assets.py` on an existing raw file.

## Python Runtime Compatibility

Do not assume `python` is available in every environment.

- Preferred interpreter order:
  - `py -3`
  - `py`
  - `python3`
  - `python`
- Use the first available interpreter to run `<skill-dir>/scripts/fetch_figma_raw.py`.
- If one command fails with "not found", retry immediately with the next interpreter.

## Command Recipes

Default node/file extraction:

```bash
py -3 <skill-dir>/scripts/fetch_figma_raw.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>"
```

Vector-fidelity extraction (geometry):

```bash
py -3 <skill-dir>/scripts/fetch_figma_raw.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>?node-id=123-456" \
  --include-geometry \
  --depth 8
```

Node render URLs (for visual cross-check):

```bash
py -3 <skill-dir>/scripts/fetch_figma_raw.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>?node-id=123-456" \
  --include-render-image-urls \
  --render-format png \
  --render-scale 2
```

Disable file-level fill asset URLs:

```bash
py -3 <skill-dir>/scripts/fetch_figma_raw.py \
  --file-key "<FILE_KEY>" \
  --node-ids "123:456,789:1011" \
  --no-asset-urls
```

Disable automatic SVG icon URL extraction:

```bash
py -3 <skill-dir>/scripts/fetch_figma_raw.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>?node-id=123-456" \
  --no-auto-svg-icon-urls
```

Disable SVG XML inline content while keeping automatic SVG icon URL extraction:

```bash
py -3 <skill-dir>/scripts/fetch_figma_raw.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>?node-id=123-456" \
  --no-inline-svg-icon-content
```

Generate optional SVG hash manifest and cache files from a raw artifact:

```bash
py -3 <skill-dir>/scripts/export_svg_assets.py \
  --raw-json "spec/figma/<EXTRACTED>-raw.json"
```

Generate raw output and SVG hash manifest in one command:

```bash
py -3 <skill-dir>/scripts/fetch_figma_raw.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>?node-id=123-456" \
  --export-svg-manifest
```

Disable default SVG hash manifest export:

```bash
py -3 <skill-dir>/scripts/fetch_figma_raw.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>?node-id=123-456" \
  --no-export-svg-manifest
```

## Output Contract

Output location rules:

- Always write to `spec/figma`.
- Do not expose or accept output path overrides.

Raw output may include these supplemental fields:

- `_figma_used_asset_refs`
  - Sorted `imageRef` values found in returned subtree.
- `_figma_fill_images`
  - Filtered payload from `GET /v1/files/:file_key/images`.
- `_figma_fill_images_by_ref`
  - Flattened `imageRef -> url` map derived from `_figma_fill_images`.
- `_figma_fill_images_error`
  - Error string when fill image call fails.
- `_figma_render_images`
  - Raw payload from `GET /v1/images/:file_key` (opt-in).
- `_figma_render_images_by_node_id`
  - Flattened `nodeId -> url` map derived from `_figma_render_images`.
- `_figma_render_images_error`
  - Error string when render image call fails.
- `_figma_svg_icon_nodes`
  - Auto-detected vector/icon-like nodes as `{id, type, name}`.
- `_figma_svg_icon_nodes_total`
  - Total auto-detected SVG candidate node count.
- `_figma_svg_icon_nodes_selected`
  - Candidate count selected for SVG URL request after applying limit.
- `_figma_svg_icon_nodes_truncated`
  - Present when selected count is lower than total due to `--auto-svg-icon-limit`.
- `_figma_svg_icon_node_ids`
  - Node ids used for automatic `format=svg` render URL request.
- `_figma_svg_icon_images`
  - Raw payload from automatic `GET /v1/images/:file_key?format=svg`.
- `_figma_svg_icon_images_by_node_id`
  - Flattened `nodeId -> svgUrl` map derived from `_figma_svg_icon_images`.
- `_figma_svg_icon_assets`
  - Convenience list `{id, type, name, svg_url}`.
- `_figma_svg_icon_images_error`
  - Error string when automatic SVG icon URL request fails.
- `_figma_svg_icon_xml_by_node_id`
  - Flattened `nodeId -> svgXml` map downloaded from auto SVG icon URLs.
- `_figma_svg_icon_xml_errors_by_node_id`
  - Per-node error map when SVG XML download fails.

Optional post-processing output from `<skill-dir>/scripts/export_svg_assets.py`:

- Sibling manifest: `spec/figma/*-svg-manifest.json`
  - Includes `assets[]` entries with `node_id`, `name`, `type`, `svg_url`, `svg_hash`, and `cached_svg_path`.
- Cached SVG files: `spec/figma/assets/svg/<sha256>.svg`
  - Hash is generated from normalized SVG XML content.

The same SVG manifest/cache artifacts are produced by default when `fetch_figma_raw.py` runs.

## Troubleshooting

- `_figma_fill_images_by_ref` is empty and `_figma_used_asset_refs` is empty
  - Selected nodes likely have no `IMAGE` fills. This is not an extractor failure.
- `_figma_used_asset_refs` is non-empty but `_figma_fill_images_by_ref` is empty
  - Check `_figma_fill_images_error` and token scope.
- Child layers are missing
  - Re-run with higher `--depth`.
- Vector paths are missing
  - Re-run with `--include-geometry`.
- `_figma_svg_icon_nodes_total` is high but `_figma_svg_icon_nodes_selected` is low
  - Increase `--auto-svg-icon-limit` if you need more auto-exported SVG URLs.

## Guardrails

- Do not generate component code in this skill.
- Keep raw JSON as the stable script output.
- Prefer node-scoped extraction when node ids are known.
- Keep cleanup minimal and deterministic.
- Keep file-level asset URL fetching enabled unless explicitly disabled.
- Keep explicit render image fetching opt-in.

## Resources

- Main entry: `<skill-dir>/scripts/fetch_figma_raw.py`
- Optional SVG hash exporter: `<skill-dir>/scripts/export_svg_assets.py`
- Shared helpers: `<skill-dir>/scripts/figma_common.py`
- Endpoint notes: `<skill-dir>/references/figma-rest-endpoints.md`
