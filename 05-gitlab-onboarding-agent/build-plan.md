# GitLab Build Plan — Blast Radius

## Goal
Ship a GitLab-track demo where a Gemini-powered agent detects a critical dependency issue, ranks affected services, opens patch merge requests, runs GitLab security pipelines, and deploys the safest fix to Cloud Run.

## Day 1: Validate access and reduce risk
- Confirm the GitLab environment supports the **official MCP server** and OAuth flow.
- Confirm the GitLab tier and feature flags needed for MCP are available.
- Set up GCP project, billing, Vertex AI, Cloud Run, Artifact Registry, and Secret Manager.
- Create the minimal GitLab group with **5-8 demo services**.
- Write the service catalog that the agent will ground on:
  - service owner
  - severity tier
  - public vs internal
  - Cloud Run target service
  - patch policy

## Day 2: Build the read path
- Ingest the mock CVE input.
- Read service catalog and runbooks from Agent Builder data stores.
- Use GitLab MCP to inspect:
  - dependency files
  - recent pipelines
  - deployment state
  - ownership metadata
- Produce a per-service risk score with a simple, explicit formula.

## Day 3: Build the write path
- Create the incident issue automatically.
- Open patch branches and merge requests for affected services.
- Add MR descriptions that explain:
  - why this service is affected
  - why the fix version was chosen
  - whether deploy is safe or blocked
- Post comments linking the MRs back to the incident issue.

## Day 4: CI/CD and secure deploy
- Add `.gitlab-ci.yml` with:
  - dependency scanning
  - SAST
  - secret detection
  - Artifact Registry upload
  - Cloud Run deployment
- Configure **Workload Identity Federation** instead of service account keys.
- Prove one service can go from MR -> pipeline -> Cloud Run deploy cleanly.

## Day 5: UX and reasoning
- Build a simple incident dashboard with:
  - live reasoning stream
  - affected services list
  - risk score
  - MR links
  - pipeline status
  - deploy status
- Keep the visuals simple and legible for a 3-minute video.

## Day 6: Script the demo
- Freeze the scenario:
  - 1 critical package
  - 3 affected services
  - 1 safe auto-deploy
  - 1 human-approval stop
  - 1 non-affected service for contrast
- Record at least 3 clean reference runs.
- Tighten prompts until the summary language is consistent and short.

## Day 7: Polish submission assets
- Record the final demo video.
- Write the Devpost narrative:
  - what problem it solves
  - why GitLab is essential
  - how Google Cloud powers the agent
  - what security controls are in place
- Verify the hosted URL works without auth barriers.

## Scope guardrails
- Do not build a generic security copilot.
- Do not scan dozens of repos.
- Do not try to support every language ecosystem.
- Do not auto-merge production fixes without a deliberate human approval step.

## Minimum winning demo
- 5-8 GitLab repos in one group
- 1 shared vulnerable dependency
- 3 affected services with distinct severity
- Incident issue created automatically
- 2 patch MRs opened automatically
- Security pipeline visible in GitLab
- 1 successful Cloud Run deployment
- 1 blocked deployment requiring approval

## Resource checklist
- Devpost resource hub: `https://rapid-agent.devpost.com/resources`
- GitLab MCP server docs: `https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/`
- GitLab secure deploy guide: `https://about.gitlab.com/blog/fast-and-secure-ai-agent-deployment-to-google-cloud-with-gitlab/`
- Cloud Run agent codelab: `https://codelabs.developers.google.com/codelabs/cloud-run/use-mcp-server-on-cloud-run-with-an-adk-agent`

## Fallback if official GitLab MCP access is blocked
- Stop before overbuilding.
- Re-scope the demo around read + write operations available in the accessible GitLab surface.
- Preserve the same story: identify exposure, open MRs, run pipelines, summarize the incident.
