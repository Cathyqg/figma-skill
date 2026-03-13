# Extraction Workflow

Use this reference when refreshing or troubleshooting Figma raw data.

## Goals

- Produce a stable raw JSON artifact from official Figma REST endpoints.
- Keep processing deterministic and minimal.
- Generate SVG hash manifest and cache artifacts by default.

## Inputs

- `--figma-url` is the preferred entrypoint.
- `--file-key` overrides the file key parsed from the URL.
- `--node-id` or `--node-ids` scopes extraction when a node is known.
- `FIGMA_TOKEN` is required unless the environment already injects it under another name and you override `--token-env`.

## Output Rules

- Always write to `spec/figma`.
- Do not add custom output path arguments.
- Prefer node-scoped extraction when a node id is known.

## Default Command

```bash
py -3 <skill-dir>/scripts/fetch_figma_raw.py \
  --figma-url "<FIGMA_URL>"
```

## Re-Extraction Matrix

- Missing child layers:
  Re-run with higher `--depth` such as `4 -> 8 -> 12`.
- Missing node id:
  Re-run discovery without node ids and start with `--discovery-depth 1`.
- Missing vector path fidelity:
  Add `--include-geometry`.
- Need screenshot-like node previews:
  Add `--include-render-image-urls`.
- Need plugin-owned metadata:
  Add `--plugin-data <VALUE>`.
- Payload too large and fill images are irrelevant:
  Add `--no-asset-urls`.

Do not re-run extraction without a concrete missing signal.

## Default Supplemental Data

The extractor already tries to enrich the raw payload with:

- `_figma_fill_images_by_ref`
- `_figma_svg_icon_images_by_node_id`
- `_figma_svg_icon_xml_by_node_id`
- `*-svg-manifest.json`
- `spec/figma/assets/svg/<sha256>.svg`

Explicit node render URLs remain opt-in via `--include-render-image-urls`.

## Manifest Fallback

If a raw artifact exists but the SVG manifest is missing, run:

```bash
py -3 <skill-dir>/scripts/export_svg_assets.py \
  --raw-json "spec/figma/<ARTIFACT>-raw.json"
```

## Troubleshooting

- `_figma_fill_images_by_ref` is empty and `_figma_used_asset_refs` is empty:
  The selected nodes likely have no image fills.
- `_figma_fill_images_by_ref` is empty but `_figma_used_asset_refs` is not:
  Check `_figma_fill_images_error` and token scope.
- `_figma_svg_icon_nodes_total` is much larger than `_figma_svg_icon_nodes_selected`:
  Raise `--auto-svg-icon-limit` only if you need more exported SVGs.
- Endpoint behavior is unclear:
  Read [figma-rest-endpoints.md](./figma-rest-endpoints.md).
