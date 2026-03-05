---
name: figma-component-implementer
description: Implement or extend React components from Figma raw context and an existing codebase. Use after figma-context-extractor when the task is Figma-to-code mapping, component reuse decisions, Storybook alignment, and repository-consistent implementation.
---

# Figma Component Implementer

## Overview

Read raw Figma JSON, inspect existing repository components first, and implement UI with reuse-first behavior. This skill does not call Figma APIs directly; it consumes artifacts from `figma-context-extractor`.

## Rule Precedence

1. Follow repository root `AGENTS.md` first.
2. Apply this skill's workflow and fallback rules next.
3. If conflict exists, treat `AGENTS.md` as repository contract.
4. Resolve ambiguity by inspecting nearby existing components before inventing new patterns.

## Required Inputs

- Raw design context file path from `figma-context-extractor`
- Target node id or explicit target UI scope
- Relevant existing component files and stories
- Repository root `AGENTS.md`
- Optional visual aids:
  - `_figma_fill_images_by_ref` for source asset URLs
  - `_figma_render_images_by_node_id` for render cross-check only

## Workflow

1. Read `AGENTS.md` and nearby component implementations before writing code.
2. Confirm raw context includes the target node and enough child depth.
3. Parse target subtree into semantic UI blocks.
4. Map blocks to existing components and BDL primitives before creating anything new.
5. Implement minimal code changes in existing repository style.
6. Update matching `*.stories.tsx` when behavior or public surface changes.
7. Validate stories against Figma data and start Storybook automatically.

## Extractor Re-run Policy

Re-running extractor is valid and effective, but only when tied to a specific missing signal.

- Missing child layers or list items
  - Re-run extractor with higher `--depth`.
- Missing vector path data for custom icon/illustration
  - Re-run with `--include-geometry`.
- Need node screenshot-style comparison
  - Re-run with `--include-render-image-urls`.
- Need plugin-owned metadata
  - Re-run with `--plugin-data`.
- No node id known
  - Re-run in discovery mode and identify target node first.

Do not re-run extractor "just in case". State the exact missing field that triggered re-extraction.

## Figma Parsing Coverage Checklist

When interpreting raw JSON, cover these fields before concluding data is missing:

- Layout and structure
  - `layoutMode`, `itemSpacing`, paddings, sizing modes, child hierarchy
- Text content
  - `characters`, font style object, line-height, alignment
- Color and style signals
  - `fills`, `strokes`, style ids, corner radius, effects
- Image assets
  - `fills[].type == IMAGE` with `imageRef`
  - Resolve image URL from `_figma_fill_images_by_ref[imageRef]`
- Vector and icon candidates
  - `VECTOR` nodes, icon-like naming, repeated symbol usage

## Interpretation Rules

- Do not translate every `FRAME` into a React component.
- Treat Figma hierarchy as evidence, not direct DOM blueprint.
- Prefer semantic layout (`flex`, `grid`, existing layout primitives) over absolute positioning.
- Treat repeated sibling structures as data-driven candidates.
- Keep component names semantic; do not expose Figma layer ids/names.

## Reuse Rules

- Reuse existing components before creating new ones.
- Extend with props/variants before cloning or rewriting.
- Follow established BDL usage from current repository code.
- Preserve existing public APIs unless user explicitly asks for breaking changes.
- Prefer existing tokens and scales over literal Figma values.

## Storybook Data Binding Contract

When component behavior or visuals change, update story data using real Figma-derived values.

- Story text and numbers
  - Use Figma `characters` and relevant numeric values for at least one baseline story.
- Story images
  - If node contains `imageRef`, wire `_figma_fill_images_by_ref` URLs into story args/fixtures.
  - Do not silently drop image data when URLs are available.
- Render URL usage
  - `_figma_render_images_by_node_id` is for visual comparison only, not production asset source.
- Missing images handling
  - If no `imageRef` exists in target subtree, state that explicitly in notes instead of fabricating URLs.

## Storybook Auto-Start

After code and stories are written, start Storybook automatically unless user explicitly disables it.

1. Use the fixed project command `npm run storybook`.
2. Default to non-blocking startup in Windows PowerShell:
   - `Start-Process -FilePath "npm.cmd" -ArgumentList @("run","storybook") -WorkingDirectory "<repo-root>"`
3. If debugging is required, run blocking command instead:
   - `npm run storybook`
4. If `package.json` does not include `storybook` script, report the missing script and stop auto-start.
5. Report the exact startup command used and expected Storybook URL.

## Fallback Rules

- If raw context remains insufficient after targeted re-extraction, deliver a minimal scaffold and list exact unknowns.
- Never invent tokens, BDL primitives, or image URLs that are not present in repository or raw data.
- Keep assumptions explicit and easy to revise.
