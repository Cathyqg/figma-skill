# Figma REST Endpoints

Use only official Figma REST endpoints in this skill.

## Authentication

- Set token in `FIGMA_TOKEN`.
- Personal Access Token (PAT): send `X-Figma-Token`.
- OAuth token: send `Authorization: Bearer <token>`.

Reference: https://developers.figma.com/docs/rest-api/authentication/

## Core Endpoints

### 1) File Discovery

- Endpoint: `GET /v1/files/{file_key}`
- Purpose: fetch file metadata and a shallow tree when node ids are not known.
- Important query params:
  - `depth`
  - `geometry=paths` (optional, expensive)
  - `plugin_data` (optional, expensive)

Reference: https://developers.figma.com/docs/rest-api/file-endpoints/

### 2) Node-Focused Extraction

- Endpoint: `GET /v1/files/{file_key}/nodes`
- Purpose: fetch selected node subtrees with controlled depth.
- Important query params:
  - `ids` (comma-separated node ids)
  - `depth`
  - `geometry=paths` (optional)
  - `plugin_data` (optional)

Reference: https://developers.figma.com/docs/rest-api/node-endpoints/

### 3) File-Level Fill Asset URLs

- Endpoint: `GET /v1/files/{file_key}/images`
- Purpose: resolve image URLs for `imageRef` values used by node fills.
- Notes:
  - Returns file-level image map.
  - The extractor filters this map to refs actually present in current payload.

Reference: https://developers.figma.com/docs/rest-api/file-endpoints/

### 4) Node Render Image URLs (Optional)

- Endpoint: `GET /v1/images/{file_key}`
- Purpose: get rendered image URLs for selected node ids.
- Important query params:
  - `ids`
  - `format`
  - `scale`

Reference: https://developers.figma.com/docs/rest-api/image-endpoints/

## Node ID Notes

- Shared links often use `node-id=123-456`.
- API expects `123:456`.
- Branch URLs are supported; prefer `/branch/<BRANCH_KEY>` when present.
- Normalize ids before calling `/nodes` or `/images`.

Reference: https://help.figma.com/hc/en-us/articles/360039823894-Get-started-with-URLs-and-links-in-Figma

## Practical Limits

- Use discovery with low depth (`1`) when node ids are unknown.
- Prefer node-focused extraction with modest depth (`4`) first.
- Raise depth only when required by missing child structure.
- Handle `429` with retry using `Retry-After`.

Reference: https://developers.figma.com/docs/rest-api/errors/
