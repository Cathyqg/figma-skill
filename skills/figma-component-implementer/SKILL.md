---
name: figma-component-implementer
description: Implement or extend React components from Figma raw context and an existing codebase. Use after figma-context-extractor for Figma-to-code mapping, component reuse decisions, Storybook updates, and repository-consistent implementation.
---

# Figma Component Implementer

## Mission

Implement or extend React components from extractor output and existing repository patterns. This skill consumes raw artifacts and does not call Figma APIs directly.

## Rule Precedence

1. Follow repository root `AGENTS.md` first.
2. Apply this skill's workflow and rules next.
3. If conflicts appear, prioritize `AGENTS.md` and adapt implementation details.

## Required Context

- Repository root `AGENTS.md`
- Raw design context file from `figma-context-extractor`
- Target node id or explicit UI scope
- Relevant existing components, styles, and `*.stories.tsx`
- Optional visual aids:
  - `_figma_fill_images_by_ref` for source image assets
  - `_figma_render_images_by_node_id` for visual cross-check only

## Execution Flow

1. Read `AGENTS.md` and nearby component implementations first.
2. Confirm raw context covers target node and required child depth.
3. If raw context is insufficient, re-run extractor using the matrix below.
4. Parse the node subtree into semantic blocks and map them to existing components/BDL primitives.
5. Implement minimal, repository-style code changes.
6. Update matching stories when behavior, visuals, or public API changes.
7. Launch Storybook and report command plus expected URL.

## Re-Extraction Matrix

- Missing child layers/list items
  - Re-run extractor with higher `--depth`.
- Missing vector path fidelity for custom icon/illustration
  - Re-run with `--include-geometry`.
- Need screenshot-like node comparison
  - Re-run with `--include-render-image-urls`.
- Need plugin-owned metadata
  - Re-run with `--plugin-data`.
- No valid target node id
  - Re-run discovery first, then extract the selected node.

Do not re-run extractor without a concrete missing signal.

## Interpretation Rules

- Treat Figma hierarchy as design evidence, not a direct DOM blueprint.
- Do not map every `FRAME` to a React component.
- Prefer semantic structure and reusable component boundaries over literal layer mirroring.

## Implementation Rules

- Treat Figma hierarchy as design evidence, not direct DOM blueprint.
- Do not map every `FRAME` to a React component.
- Prefer semantic layout (`flex`, `grid`, existing layout primitives) over absolute positioning.
- Reuse existing components before creating new ones; extend via props/variants first.
- Follow established repository usage of BDL and tokens over literal Figma values.
- Preserve existing public APIs unless a breaking change is explicitly requested.
- Convert repeated structures into data-driven render logic instead of duplicated JSX.
- Keep names semantic; never expose Figma layer ids/names in production APIs.
- When intent is ambiguous, make the smallest explicit assumption and keep code easy to revise.

## Minimal Parsing Checklist

- Layout: `layoutMode`, spacing, paddings, sizing modes, child hierarchy
- Text: `characters`, typography, alignment, line-height
- Style: fills, strokes, radius, effects, style ids
- Image: `fills[].type == IMAGE`, `imageRef`, `_figma_fill_images_by_ref`
- Vector/icon: `VECTOR` nodes and icon-like naming patterns

## Storybook Contract

- Use real Figma-derived values for at least one baseline story:
  - text from `characters`
  - relevant numeric values
- If target nodes contain `imageRef`, bind image URLs from `_figma_fill_images_by_ref`.
- Do not treat `_figma_render_images_by_node_id` as production asset source.
- If no `imageRef` exists in target scope, state that explicitly instead of fabricating URLs.

## Storybook Start Rule

Use fixed project command `npm run storybook`.

- Default non-blocking startup in bash:
  - `nohup npm run storybook > .storybook.log 2>&1 &`
- For debugging, run blocking command:
  - `npm run storybook`
- If `package.json` lacks `storybook` script, report the missing script and stop auto-start.

## Fallback Rules

- If raw context is still insufficient after targeted re-extraction, implement a minimal safe scaffold and list exact unknowns.
- Never invent tokens, BDL primitives, or image URLs that are not present in repository or extractor output.
