---
name: figma-component-implementer
description: Implement or extend React components from Figma raw design context and an existing component codebase. Use when a raw JSON artifact from figma-context-extractor is available and the task is to map design nodes to reusable components, follow repository rules, and generate or modify component code.
---

# Figma Component Implementer

## Overview

Read Figma raw design context, inspect the existing component library, and implement the target UI with reuse-first behavior. Use this skill after `figma-context-extractor`; this skill assumes the raw JSON already exists and focuses on code generation decisions, not Figma API retrieval.

## Rule Precedence

1. Follow the repository root `AGENTS.md` first.
2. Apply this skill's workflow and decision rules next.
3. When the two appear to conflict, treat `AGENTS.md` as the repository contract and adapt the implementation to it.
4. If a required repository rule is still ambiguous, inspect nearby existing components before making a new assumption.

## Required Inputs

- Raw design context file path from `figma-context-extractor`
- Target node id or explicit target UI scope
- Relevant existing component files, primitives, and design-system entry points
- Repository root `AGENTS.md`
- Repository styling rules, naming rules, and token usage rules
- Optional render image URL when a visual cross-check is needed

## Workflow

1. Read the repository root `AGENTS.md` and treat it as the baseline contract for all implementation decisions.
2. Confirm the raw design context exists and covers the target node.
3. If the raw file is missing expected layers, vectors, or assets, rerun `figma-context-extractor` with higher-cost flags before coding.
4. Read the target node subtree and identify semantic blocks such as containers, cards, list rows, form fields, actions, badges, and icons.
5. Search the repository for existing components that match the same semantic role before writing any new code.
6. Prefer extending an existing component with props, variants, or composition slots.
7. Create a new component only when reuse is clearly insufficient.
8. Implement the final code in the repository's existing style, API shape, and file structure.
9. Cross-check the result against the raw design data and any available render image.

## Interpretation Rules

- Do not translate every `FRAME` into a React component.
- Treat Figma layer hierarchy as design evidence, not as a direct DOM blueprint.
- Treat repeated sibling structures as candidate list items, cards, rows, tabs, or menu entries.
- Treat `mdi:*`, `icon-*`, and vector-only nodes as icon candidates.
- Prefer semantic layout (`flex`, `grid`, existing layout primitives) over copying raw absolute positions.
- Use exact vector geometry only when the target must reproduce a custom icon or illustration precisely.
- Use `_figma_fill_images` only as source asset references; never invent missing asset URLs.

## Component Reuse Rules

- Reuse existing components before creating new ones.
- Extend an existing component with props or variants before cloning or rewriting it.
- Obey repository-level constraints from `AGENTS.md` when deciding whether to reuse local components, BDL primitives, or both.
- Preserve the repository's public component APIs unless the user explicitly asks for a breaking change.
- Prefer existing tokens, spacing scales, typography primitives, and color roles over Figma literal values when both exist.
- Introduce new subcomponents only when they improve reuse or keep the parent component readable.
- Avoid one-off wrappers and one-off styles when an existing primitive already solves the same problem.

## Codegen Rules

- Read nearby existing components first and mirror the repository's proven usage of BDL before consulting package internals.
- Match the existing repository style for file names, exports, props, hooks, and styling.
- Keep component names semantic. Do not expose Figma-derived names like `Frame34021` as production component names.
- Keep code focused on the target UI. Do not dump unrelated nodes into the same component.
- When the design implies data-driven repetition, convert repeated structures into mapped render logic instead of copy-pasted JSX.
- When data is ambiguous, add the smallest explicit assumption needed and keep the implementation easy to revise.

## Fallback Rules

- If the raw design context is too shallow, stop and rerun `figma-context-extractor` with a higher `--depth`.
- If vector geometry is required but missing, rerun `figma-context-extractor` with `--include-geometry`.
- If no reusable component matches, create the smallest new component that still fits the design system.
- If the visual design is clear but implementation details are missing, produce a safe scaffold and call out the exact unknowns.
