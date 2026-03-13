---
name: design-to-code
description: "Convert a Figma design URL or node into repository-consistent React component code in one workflow. Use when a user provides a Figma design/file/branch URL and wants end-to-end design-to-code execution: fetch stable raw JSON into spec/figma, generate SVG hash manifests, resolve SVG asset reuse, and implement or update React components and stories using existing repository patterns."
---

# Design to Code

Use this skill as the single entrypoint for Figma-to-React work.

## Inputs

- Treat `$ARGUMENTS` as the task request.
- Prefer a Figma URL from `$ARGUMENTS`. If the URL includes `node-id`, use node-scoped extraction.
- If `$ARGUMENTS` is missing a URL, look for a Figma URL or node id in the conversation before asking.
- Require `FIGMA_TOKEN` from the environment or `.env` before any extraction.

Example invocation:

```text
/design-to-code Implement this design from Figma.
https://www.figma.com/design/<FILE_KEY>/<NAME>?node-id=123-456&m=dev
```

## Resolve The Skill Directory

- In Claude Code, prefer `${CLAUDE_SKILL_DIR}` when it is available.
- Otherwise resolve the directory that contains this `SKILL.md`.
- Treat that resolved path as `<skill-dir>` in the commands below.

## Workflow

1. Read repository root `AGENTS.md` and inspect nearby components, styles, stories, and exports before writing code.
2. Confirm whether the current workspace contains the target implementation surface such as `lib/components/`.
3. Parse the target Figma URL from `$ARGUMENTS`.
4. Refresh raw design context with `<skill-dir>/scripts/fetch_figma_raw.py` when the request contains a URL or when `spec/figma` lacks a matching artifact.
5. Keep extraction output fixed under `spec/figma`.
6. Ensure a matching `*-svg-manifest.json` exists. The extractor generates it by default; otherwise run `<skill-dir>/scripts/export_svg_assets.py`.
7. Before adding any SVG asset, run `<skill-dir>/scripts/resolve_svg_asset_reuse.py` and produce a `*-svg-reuse-report.json`.
8. If the current workspace is only a skill repo or lacks the target component directories, stop after artifact generation and report the missing implementation surface explicitly.
9. Otherwise implement or extend existing React components by treating Figma JSON as design evidence, not as a literal DOM blueprint.
10. Update the related `*.stories.tsx` file when behavior, visuals, or public API changed.
11. Run repository-native validation commands already used nearby and report any commands you could not run.

## Read These References On Demand

- Read [references/extraction-workflow.md](./references/extraction-workflow.md) before extracting or re-extracting.
- Read [references/react-implementation.md](./references/react-implementation.md) before code changes.
- Read [references/figma-rest-endpoints.md](./references/figma-rest-endpoints.md) only when endpoint behavior or payload shape is unclear.

## Default Extraction Command

Use the smallest extraction that can answer the task:

```bash
py -3 <skill-dir>/scripts/fetch_figma_raw.py \
  --figma-url "<FIGMA_URL>"
```

Python fallback order:

1. `py -3`
2. `py`
3. `python3`
4. `python`

Retry immediately with the next interpreter if one is unavailable.

## Guardrails

- Keep the workflow end-to-end inside this skill; do not require the user to invoke a second skill.
- Detect when the current workspace is not the actual component codebase. In that case, do not invent component files; stop after extraction and reuse analysis.
- Prefer reusing existing components before creating new ones.
- Prefer BDL primitives and repository tokens over literal Figma values when the codebase already has a mapping.
- Never use temporary Figma CDN URLs as production runtime asset references.
- Do not invent image URLs, BDL primitives, or tokens that are not present in repository code or extractor artifacts.
- Re-extract only for a concrete missing signal such as missing children, missing geometry, or missing render URLs.

## Deliverables

Report these outputs in the final response:

- The raw artifact written under `spec/figma`
- The SVG manifest and SVG reuse report used for implementation
- The component and story files changed, or an explicit note that no implementation surface existed in the current workspace
- Whether each SVG in scope was reused or added as new
- Validation commands run and any remaining unknowns
