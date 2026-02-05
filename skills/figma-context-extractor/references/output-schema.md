# Output Schema

The extractor writes one markdown file. The markdown contains a machine-usable JSON block.

## Top-level Markdown Sections

1. `Source`
2. `Extraction Limits`
3. `Requirement Digest` (if `--spec-file` exists)
4. `Design Summary`
5. `Warnings` (if any)
6. `Suggested Node IDs` (discovery mode only)
7. `Normalized Design JSON`

## Normalized Design JSON Shape

```json
{
  "file": {
    "key": "...",
    "name": "...",
    "version": "...",
    "lastModified": "..."
  },
  "selection": {
    "requestedNodeIds": ["123:456"],
    "resolvedRoots": ["123:456"]
  },
  "limits": {
    "maxNodes": 320,
    "maxTextChars": 280,
    "includeHidden": false,
    "includeFigJam": false
  },
  "summary": {
    "emittedNodes": 110,
    "nodeTypes": {"FRAME": 8, "TEXT": 29},
    "droppedHiddenNodes": 12,
    "droppedFigJamNodes": 0,
    "prunedByNodeLimit": 0,
    "truncatedTextNodes": 4
  },
  "references": {
    "styles": {},
    "components": {},
    "componentSets": {}
  },
  "images": {},
  "roots": []
}
```

## Node Shape (`roots[]` and descendants)

- `id`, `name`, `type`, `path`
- `bounds`: `x/y/width/height`
- `layout`: auto-layout and sizing fields
- `appearance`: fills, strokes, effects, radius, opacity
- `text`: content + selected typography fields (`TEXT` only)
- `component`: instance linkage and component properties
- `children`: nested nodes

## Filtering Rules

- Drop empty/null fields
- Truncate long text node content by `maxTextChars`
- Stop emitting when `maxNodes` is reached
- By default remove hidden nodes and FigJam-only types
