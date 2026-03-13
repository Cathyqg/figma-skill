# React Implementation Workflow

Use this reference before translating raw Figma artifacts into component code.

## Rule Order

1. Follow repository root `AGENTS.md`.
2. Follow the target component's existing patterns under `lib/components/`.
3. Apply this workflow.

## Inputs

- The selected raw artifact under `spec/figma`
- The matching `*-svg-manifest.json`
- The matching `*-svg-reuse-report.json`
- Nearby components, utilities, styles, stories, and exports

If the workspace does not contain the expected implementation surface such as `lib/components/`, stop here and report that the current repository is not the component codebase.

## Execution Flow

1. Inspect the target component and related components first.
2. If the expected component directories do not exist, do not fabricate them. Return the extracted artifacts and the exact repository gap.
3. Confirm the raw artifact contains the target node and enough child depth.
4. Run SVG reuse resolution before adding any new SVG file:

```bash
py -3 <skill-dir>/scripts/resolve_svg_asset_reuse.py
```

5. Parse the Figma subtree into semantic blocks.
6. Map those blocks onto existing components or BDL primitives.
7. Implement the smallest repository-consistent code change.
8. Update stories when behavior, visuals, or public API changed.

## Interpretation Rules

- Treat Figma hierarchy as design evidence, not as a literal JSX tree.
- Do not map every frame into a React component.
- Prefer semantic `flex`, `grid`, and existing layout primitives over absolute positioning.
- Preserve existing public APIs unless the task explicitly asks for a change.
- Convert repeated structures into data-driven render logic rather than duplicated JSX.

## SVG Reuse Contract

- Prefer reusing an existing repository SVG before creating a new file.
- Use manifest `assets[].svg_hash` as the primary dedupe key.
- Use the reuse report as the source of truth for `reuse` versus `new`.
- If the report says `reuse`, wire the existing asset path or export.
- If the report says `new`, add the SVG only inside the repository's existing asset structure.
- Never ship a Figma render URL or CDN SVG URL as a runtime asset.

## Stories And Validation

- Update the matching `*.stories.tsx` file when present.
- Use real Figma-derived values for at least one baseline example when the story surface changed.
- Prefer repository-native validation commands already used by nearby components.
- If validation cannot run, state that explicitly in the final report.
