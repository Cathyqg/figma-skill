---
name: figma-context-extractor
description: Fetch raw Figma REST data for downstream UI implementation. Use when a user provides a Figma URL or node ids and needs stable JSON artifacts (including image asset URLs by default and optional render URLs) before component coding.
---

# Figma Context Extractor

## Goal

Produce a stable raw JSON artifact from official Figma REST endpoints. Keep script-side processing minimal and deterministic.

## Required Inputs

- `figma_url` or `file_key` (required)
  - Branch URLs are supported. If `/branch/<BRANCH_KEY>` exists, use branch key first.
- `FIGMA_TOKEN` (required by default)
- `node_id` list (recommended for node-scoped extraction)
- `FIGMA_OUTPUT_DIR` (optional default output directory)
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

- `--output`
  - Full output file path. Highest priority.
- `--output-dir`
  - Output directory. Used when `--output` is not set.
- `--output-name`
  - Output filename inside `--output-dir`.
- Resolution order
  - `--output` -> `--output-dir` -> `FIGMA_OUTPUT_DIR` -> `tmp/figma`
- Team convention
  - Use `FIGMA_OUTPUT_DIR` as default and omit `--output-dir` in normal commands.
  - Pass `--output-dir` only for temporary per-run override.

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
4. Only when requested, run `GET /v1/images/:file_key` for node render URLs.
5. Write one stable raw JSON file and return raw JSON only.

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

## Output Contract

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

## Troubleshooting

- `_figma_fill_images_by_ref` is empty and `_figma_used_asset_refs` is empty
  - Selected nodes likely have no `IMAGE` fills. This is not an extractor failure.
- `_figma_used_asset_refs` is non-empty but `_figma_fill_images_by_ref` is empty
  - Check `_figma_fill_images_error` and token scope.
- Child layers are missing
  - Re-run with higher `--depth`.
- Vector paths are missing
  - Re-run with `--include-geometry`.

## Guardrails

- Do not generate component code in this skill.
- Keep raw JSON as the stable script output.
- Prefer node-scoped extraction when node ids are known.
- Keep cleanup minimal and deterministic.
- Keep file-level asset URL fetching enabled unless explicitly disabled.
- Keep render image fetching opt-in.

## Resources

- Main entry: `<skill-dir>/scripts/fetch_figma_raw.py`
- Shared helpers: `<skill-dir>/scripts/figma_common.py`
- Endpoint notes: `<skill-dir>/references/figma-rest-endpoints.md`
