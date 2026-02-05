# Spec Integration Notes

Use this skill together with spec-generator output.

## Expected Input

- A markdown spec file, typically like `specs/<feature>/spec.md`
- The extractor reads headings, bullet lists, and requirement-like lines
- It creates a concise digest and embeds it into the Figma context markdown

## Why Digest Instead of Full Spec

- Keep context small for downstream agents
- Preserve requirement anchors (headings, scenarios, acceptance bullets)
- Avoid repeating full requirement documents

## Recommended Pipeline

1. Generate or update requirement spec markdown
2. Run Figma discovery to pick node ids
3. Run focused extraction with `--spec-file`
4. Give only `spec.md` plus `figma-context.md` to code-generation skill

## Suggested File Layout

```text
specs/
  123-login-flow/
    spec.md
    figma-context.discovery.md
    figma-context.md
```
