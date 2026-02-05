---
name: figma-context-extractor
description: Fetch and condense Figma design data through official REST API endpoints into compact markdown plus normalized JSON for React+TypeScript implementation planning. Use when a user provides a Figma URL or node ids and needs clean, codegen-ready design context (not component code generation), especially when combining design with a spec markdown from a spec-generator workflow.
---

# Figma Context Extractor

## Goal

Produce a markdown context file that keeps only implementation-relevant design data and avoids token explosion.

## Inputs

Collect these inputs before running extraction:

- `figma_url` or `file_key` (required)
- `node_id` list (recommended; if absent, run discovery mode first)
- `spec_file` markdown path from spec workflow (optional)
- `FIGMA_TOKEN` environment variable (required by default)
- `auth_mode` (optional): `pat` default; use `oauth` only for OAuth bearer tokens
- `env_file` (optional): defaults to `.env`, used when env var is missing

## Workflow

1. Resolve `file_key` and optional `node-id` values from the Figma URL.
2. Run discovery mode when no node id is present.
3. Use discovery output to pick target node ids.
4. Run focused extraction on selected nodes.
5. Merge a concise digest from `spec_file` when provided.
6. Return a markdown report with summary, warnings, and normalized JSON payload.

## Command Recipes

Use discovery mode first when user only gives a file URL:

```bash
python skills/figma-context-extractor/scripts/build_figma_context.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>" \
  --output specs/<feature>/figma-context.discovery.md
```

Run focused extraction (preferred for downstream code generation):

```bash
python skills/figma-context-extractor/scripts/build_figma_context.py \
  --figma-url "https://www.figma.com/design/<FILE_KEY>/<NAME>?node-id=123-456" \
  --node-id "789:1011" \
  --spec-file specs/<feature>/spec.md \
  --output specs/<feature>/figma-context.md \
  --depth 4 \
  --max-nodes 320 \
  --max-text-chars 280
```

Use export URLs only when screenshots are needed:

```bash
python skills/figma-context-extractor/scripts/build_figma_context.py \
  --file-key "<FILE_KEY>" \
  --node-ids "123:456,789:1011" \
  --include-image-urls \
  --output specs/<feature>/figma-context.md
```

## Output Contract

The generated markdown always includes:

- `Source`: mode, endpoint, selected node ids, retrieval time
- `Extraction Limits`: depth and token-protection limits
- `Requirement Digest`: compact excerpt from spec markdown when provided
- `Design Summary`: emitted/dropped/pruned counts and node type histogram
- `Warnings`: missing nodes, truncation, or discovery-only notices
- `Normalized Design JSON`: structured payload for downstream component generation

## Guardrails

- Do not generate component code in this skill.
- Prefer node-scoped extraction over full-file extraction.
- Keep defaults unless user explicitly asks for deeper output:
  - `max_nodes=320`
  - `max_text_chars=280`
  - hidden nodes removed
  - FigJam node types removed
- Raise actionable warnings when data is missing or truncated.

## Resources

- Main script: `scripts/build_figma_context.py`
- Raw test script: `scripts/fetch_figma_raw.py` (does not affect normal flow)
- Endpoint notes: `references/figma-rest-endpoints.md`
- Output schema details: `references/output-schema.md`
