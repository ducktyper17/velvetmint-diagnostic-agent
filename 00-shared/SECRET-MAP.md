# Shared Secret Map

Canonical secret store for this workspace: **Google Secret Manager** in project
`project-30c02ca7-9a98-43f5-be9`.

Local `.env` files remain gitignored and are only for local development
convenience. They should mirror values from Secret Manager, not become the
source of truth.

## Naming convention

Use lower-kebab-case names, prefixed with `hackathon-`.

Examples:

- `hackathon-fivetran-api-key`
- `hackathon-fivetran-api-secret`
- `hackathon-fivetran-mcp-token`
- `hackathon-mongodb-uri`
- `hackathon-arize-api-key`
- `hackathon-elastic-api-key`
- `hackathon-gitlab-token`
- `hackathon-dynatrace-api-token`

## Planned secrets by track

### Shared / cross-project

- `hackathon-mongodb-uri`
- `hackathon-github-token` (optional)
- `hackathon-google-cloud-project-id` (optional convenience)

### 01 Fivetran

- `hackathon-fivetran-api-key`
- `hackathon-fivetran-api-secret`
- `hackathon-fivetran-mcp-token`

### 02 Arize

- `hackathon-arize-api-key`
- `hackathon-arize-space-id` (if needed)

### 03 MongoDB

- `hackathon-mongodb-uri`
- `hackathon-voyage-api-key` (only if this backup is activated)

### 04 Elastic

- `hackathon-elastic-cloud-id`
- `hackathon-elastic-api-key`

### 05 GitLab

- `hackathon-gitlab-token`
- `hackathon-gitlab-instance-url` (if self-managed)

### 06 Dynatrace

- `hackathon-dynatrace-environment-url`
- `hackathon-dynatrace-api-token`

## Local dev mirrors

When a local service needs secrets, map them into that project's gitignored
`.env` file using the variable names expected by that app.

Example for the Fivetran agent:

- `FIVETRAN_MCP_TOKEN <- hackathon-fivetran-mcp-token`
- `MONGODB_URI <- hackathon-mongodb-uri`

The raw Fivetran API key/secret are expected by the standalone MCP server,
not by the agent service itself.
