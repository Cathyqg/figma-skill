---
name: figma-context-extractor
description: Fetch Figma design data through official REST API endpoints with a single raw-only script. The stable artifact is the raw JSON response, with file-level image fill asset URLs included by default and node render image URLs available as an explicit option. Use when a user provides a Figma URL or node ids and needs design context for downstream React+TypeScript work (not component code generation).
---

# Figma Context Extractor

## Goal

Produce a stable raw Figma JSON artifact. Keep script-side processing minimal and do any lightweight cleanup in the skill prompt itself.

## Inputs

Collect these inputs before running extraction:

- `figma_url` or `file_key` (required)
  - Branch URLs are supported; if `/branch/<BRANCH_KEY>` exists it is used automatically.
- `node_id` list (recommended; if absent, the raw stage can still run in discovery/full-file mode)
- `FIGMA_TOKEN` environment variable (required by default)
- `FIGMA_OUTPUT_DIR` environment variable (optional): default output directory for generated raw/context files
- `auth_mode` (optional): `pat` default; use `oauth` only for OAuth bearer tokens
- `env_file` (optional): defaults to `.env`, used when env var is missing
- `no_asset_urls` (optional): disable the supplemental file-level image asset URL call
  - Backward-compatible alias: `no_fill_image_urls`
- `include_render_image_urls` (optional): enable node render image URLs for selected node ids

## Parameter Rules

- `--include-geometry`
  - Enable only when the user needs vector fidelity, such as recreating icons, logos, or custom SVG paths.
  - This adds `geometry=paths` to the Figma request and increases payload size.
  - Leave it off for layout, text, spacing, color, and general code-structure extraction.
- `--depth`
  - Start with `4` for node-scoped extraction.
  - Raise to `8` or higher when expected child layers, nested assets, or deeper structure are missing.
  - Keep it as low as possible on large frames to avoid oversized raw payloads.
- `--discovery-depth`
  - Use `1` for lightweight file discovery when no node id is known.
  - Increase only if the top-level structure is too shallow to identify the correct target node.
- `--no-asset-urls`
  - Keep asset URL fetching enabled by default.
  - Disable it only when the user explicitly wants the smallest possible payload or does not need image assets.
- `--include-render-image-urls`
  - Enable it only when the user needs a rendered preview/export of the selected node.
  - Keep it off when the user only needs source design data and asset references.
- Agent behavior
  - Do not enumerate every possible flag in normal usage.
  - Do apply these rules when choosing high-impact flags.
  - When the task is ambiguous, prefer smaller payloads first, then rerun with higher-cost flags only if the result is insufficient.

## Workflow

1. Resolve `file_key` and optional `node-id` values from the Figma URL.
2. Call the Figma file endpoint and keep the full response as the primary artifact.
3. By default, also call `GET /v1/files/:file_key/images`, then keep only the asset URLs whose `imageRef` values are actually used in the returned node subtree.
4. Only when render previews are explicitly requested, call `GET /v1/images/:file_key` for the selected node ids.
5. If no node id is present, use the raw discovery/full-file payload to choose target node ids.
6. Do only lightweight cleanup in the skill itself, such as selecting relevant nodes or fields for the next agent step.
7. Return raw JSON only.

## Command Recipes

Default raw-only entry point:

```bash
python skills/figma-context-extractor/scripts/fetch_figma_raw.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>" \
  --output-dir specs/<feature>
```

Fetch selected nodes and also include node render image URLs:

```bash
python skills/figma-context-extractor/scripts/fetch_figma_raw.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>?node-id=123-456" \
  --node-id "789:1011" \
  --include-render-image-urls \
  --output-dir specs/<feature> \
  --depth 4
```

Disable file-level image asset URLs when you only want the file/nodes payload:

```bash
python skills/figma-context-extractor/scripts/fetch_figma_raw.py \
  --file-key "<FILE_KEY>" \
  --node-ids "123:456,789:1011" \
  --no-asset-urls \
  --output-dir specs/<feature>
```

## Output Contract

The raw stage always produces:

- Full JSON from `GET /v1/files/:file_key` or `GET /v1/files/:file_key/nodes`
- The extracted `imageRef` list from the returned payload, in `_figma_used_asset_refs`
- Only the file-level image fill asset URLs actually referenced by the returned node subtree, in `_figma_fill_images`
- File-level image asset fetch errors in `_figma_fill_images_error` when the main payload succeeds but the image asset call fails
- Node render image URLs in `_figma_render_images` only when `--include-render-image-urls` is used
- Node render image fetch errors in `_figma_render_images_error` when the main payload succeeds but the render image call fails
- A stable file written to `FIGMA_OUTPUT_DIR` (or an explicit output path)

## Guardrails

- Do not generate component code in this skill.
- Prefer raw JSON as the stable and only script output.
- Prefer node-scoped extraction over full-file extraction when node ids are known.
- Keep script-side cleanup minimal.
- Do any simple trimming or summarization in the skill instructions, not in Python, unless the raw payload format proves insufficient.
- Keep file-level image asset URL fetching enabled by default unless the user explicitly disables it.
- Filter asset URLs down to the `imageRef` values actually present in the returned payload, instead of keeping the whole file-wide asset map.
- Inspect `_figma_used_asset_refs` first when debugging why `_figma_fill_images` is empty.
- Keep node render image URL fetching opt-in because it is a different artifact from source image assets.

## Resources

- Main entry: `scripts/fetch_figma_raw.py`
- Shared helpers: `scripts/figma_common.py`
- Endpoint notes: `references/figma-rest-endpoints.md`
