# AGENTS.md

## Repository Expectations

- This repository is a React component library.
- Primary implementation code lives under `lib/components/`.
- A component directory may include files such as `*.tsx`, `*.ts`, `*.scss`, and `*.stories.tsx`.
- Follow the existing repository structure, naming, export style, and file organization before introducing any new patterns.

## UI Implementation Rules

- Prefer modifying or extending an existing component before creating a new one.
- Treat Figma design data as implementation evidence, not as a direct frame-to-div blueprint.
- Preserve semantic component boundaries. Do not expose Figma layer names such as `Frame34021` as production component names.
- Prefer semantic layout using existing layout patterns over copying raw absolute positioning.
- Keep changes minimal and aligned with the current codebase style.

## BDL Rules

- Prefer the internal BDL component library for all foundational UI building blocks.
- Do not re-implement basic primitives that BDL already provides.
- Prefer BDL design tokens over hard-coded literal values when both are available.
- When modifying or creating a component, first inspect existing components in `lib/components/` to learn how BDL is already used in this repository.
- Treat existing repository usage as the source of truth before consulting package internals.

## Reading Strategy

- First inspect the target component and nearby related components in `lib/components/`.
- Next inspect shared local utilities, styles, and stories used by those components.
- Read `node_modules` only when a specific BDL component API is unclear from existing repository code.
- Do not scan `node_modules` broadly. Only read the minimum files needed for the specific BDL component in question.

## Figma Workflow

- Use `skills/figma-context-extractor/` to retrieve raw Figma design context when design data must be refreshed.
- Use `skills/figma-component-implementer/` to interpret Figma raw data and decide how to implement or extend React components.
- Keep extractor output deterministic under `spec/figma` and generate SVG manifest/cache artifacts by default.
- Run SVG hash reuse resolution before component code changes and report reuse/new decisions.
- Re-run the extractor with higher-cost flags only when the current raw payload is insufficient for the task.

## Asset Reuse Rules

- Treat SVG URLs/XML extracted from Figma as candidate sources, not production runtime URLs.
- Before adding a new SVG asset, try reusing an existing project asset by deterministic hash of normalized SVG content.
- Add a new SVG file only when no existing asset matches the normalized hash.
- Keep new SVG assets in the repository's existing asset directories and export flow; do not invent parallel asset structures.

## Stories And Validation

- When a component behavior or public surface changes, inspect and update the matching `*.stories.tsx` file when present.
- Keep examples and stories consistent with the implemented API.
- Prefer repository-native validation commands and patterns already used by nearby components.

## Missing BDL Mapping

- A complete BDL mapping is not required to start using this repository guidance.
- When no explicit BDL mapping exists, infer the preferred BDL usage from existing components and imports in `lib/components/`.
- If a repeated mapping pattern becomes clear, it can be documented later in a dedicated reference file or a nested `AGENTS.md`.
- Until a formal mapping is added, do not invent new BDL conventions if existing repository usage already suggests a pattern.
