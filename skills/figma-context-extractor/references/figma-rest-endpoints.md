# Figma REST Endpoints

Use only official Figma REST endpoints for this skill.

## Authentication

- Set token in `FIGMA_TOKEN`
- Personal Access Token (PAT): send `X-Figma-Token`
- OAuth token: send `Authorization: Bearer <token>`

Reference: https://developers.figma.com/docs/rest-api/authentication/

## Core Endpoints

### 1) File discovery

- Endpoint: `GET /v1/files/{file_key}`
- Purpose: get file metadata and a shallow tree for discovery
- Important query params:
  - `depth`: limit tree depth to reduce payload
  - `geometry=paths`: optional vector geometry, expensive
  - `plugin_data`: optional plugin payload, expensive

Reference: https://developers.figma.com/docs/rest-api/file-endpoints/

### 2) Node-focused extraction

- Endpoint: `GET /v1/files/{file_key}/nodes`
- Purpose: pull only selected node subtrees
- Important query params:
  - `ids`: comma-separated node ids
  - `depth`: subtree depth limit
  - `geometry=paths`, `plugin_data`: optional when needed

Reference: https://developers.figma.com/docs/rest-api/node-endpoints/

### 3) Optional image export URLs

- Endpoint: `GET /v1/images/{file_key}`
- Purpose: resolve export URLs for selected nodes
- Important query params:
  - `ids`, `format`, `scale`

Reference: https://developers.figma.com/docs/rest-api/image-endpoints/

## Node ID Notes

- Shared links often use `node-id=123-456`
- API expects `123:456`
- Always normalize before calling `/nodes`

Reference: https://help.figma.com/hc/en-us/articles/360039823894-Get-started-with-URLs-and-links-in-Figma

## Practical Limits

- Prefer discovery (`depth=2`) first
- Then extract selected node ids (`depth=3~5`)
- Handle `429` with retry using `Retry-After`

Reference: https://developers.figma.com/docs/rest-api/errors/
