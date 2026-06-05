# Track 5: GitLab — Blast Radius (Zero-Day Response Agent)

> **This replaces the old onboarding concept.** If we pursue GitLab, this is the stronger path.

## One-liner
*"Critical CVE -> prioritized patch MRs and a safe Cloud Run deploy in 90 seconds."* When a new vulnerability lands, the agent scans GitLab projects, determines which services are actually exposed, opens fix MRs, runs security pipelines, and produces a clean incident summary for engineering leadership.

## Why this is the better GitLab idea
- **The pain is universal and urgent.** Every engineering org has a zero-day panic story.
- **The demo is dramatic.** Judges see multiple MRs, pipelines, and deployment updates appear live in GitLab.
- **GitLab is load-bearing, not decorative.** The agent uses GitLab for source, CI/CD, security scans, environments, and merge requests.
- **It maps cleanly onto the judging rubric.** Technical depth is obvious, impact is easy to explain, and the output is visually legible in under 3 minutes.

## What the agent does
1. Receives a new CVE or GitLab vulnerability alert.
2. Reads a grounded service catalog and runbooks from Google Cloud Agent Builder data stores.
3. Uses the **official GitLab MCP server** to inspect group projects, lockfiles, dependency scan results, owners, pipelines, and deployment state.
4. Scores blast radius by production exposure, service criticality, and fix confidence.
5. Creates a prioritized incident issue in GitLab.
6. Opens patch branches and merge requests with human-readable explanations.
7. Triggers or observes GitLab CI pipelines with dependency scanning, SAST, and secret detection.
8. If the green path is reached, deploys patched services to Cloud Run through GitLab CI/CD.
9. Publishes an executive incident summary: affected services, critical services, patch status, and next approvals needed.

## Why this can win
### Technological Implementation
- Uses **Gemini + Google Cloud Agent Builder**, which the rules explicitly require.
- Uses the **official GitLab MCP server over HTTP/OAuth**, not a toy wrapper.
- Demonstrates real multi-step action: inspect repos, write MRs, run pipelines, and deploy.
- Leans into GitLab's strongest surface area: code + security + CI/CD + environments.

### Design
- The UI can show a live "blast radius board" with streaming reasoning and a per-service risk score.
- The final output is crisp: `critical now`, `safe to patch`, `already mitigated`, `needs human review`.

### Potential Impact
- Security patch response is a board-level problem, not an internal productivity nicety.
- The value is instantly legible: "hours or days of security triage compressed into minutes."

### Quality of the Idea
- Most GitLab hackathon entries will be code review helpers or generic DevOps copilots.
- "Runtime-aware security response with auto-created patch MRs and safe deploy flow" is more memorable than "AI helps developers work faster."

## Resource-backed architecture
This path uses the strongest parts of the official hackathon resource stack:

### Phase 1: Core frameworks & environment
- **Gemini + Google Cloud Agent Builder** for the reasoning layer.
- GCP free trial or hackathon credits for infrastructure.

### Phase 2: Action mechanisms & grounding
- **Official GitLab MCP server** with HTTP transport and OAuth.
- **Agent Builder data stores** for runbooks, service ownership docs, severity policy, and deployment playbooks.

### Phase 3: Partner integration & infrastructure
- GitLab is the partner system of record for repos, MRs, pipelines, security scans, and environments.

### Phase 4: Reasoning, state, and hosting
- **Secret Manager** for tokens, webhook secrets, and environment configuration.
- **Cloud Run** for the agent backend and demo app.

### Phase 5: Deployment & safety
- **GitLab CI/CD -> Artifact Registry -> Cloud Run** using Workload Identity Federation.
- GitLab security templates for **dependency scanning**, **SAST**, and **secret detection**.
- Gemini safety settings for guardrails around automated remediation suggestions.

## Core demo flow (3 minutes)
- **0:00-0:15**: Hook. "A critical package CVE lands. Security teams usually spend half a day figuring out what matters."
- **0:15-0:35**: Show the CVE alert or incident trigger.
- **0:35-1:30**: Stream the agent's reasoning: scanning projects, checking ownership, ranking blast radius, identifying safe fixes.
- **1:30-2:15**: Cut to GitLab. Merge requests are open, incident issue exists, pipelines are running, and risk labels are attached.
- **2:15-2:40**: Show Cloud Run deployment result for the low-risk service path and the blocked path for services needing manual approval.
- **2:40-3:00**: Close on the incident summary dashboard: "7 services scanned, 3 affected, 2 patch MRs opened, 1 safe deploy completed."

## What to build first
- A **fake but believable GitLab group** with 5-8 services, not 20+ repos.
- One mock CVE affecting a shared dependency.
- A clean service catalog: owner, tier, public/private, Cloud Run service name, patch policy.
- One golden path where the patch is safe and auto-deploys.
- One red path where the agent stops and asks for human approval.

See `05-gitlab-onboarding-agent/build-plan.md` for the execution plan.

## Critical implementation notes
- Prefer the **official GitLab MCP server** first. It is beta and requires the right GitLab tier, so validate access on day 1.
- Use HTTP transport with OAuth, as documented by GitLab, to avoid extra local plumbing.
- Keep the partner story centered on GitLab. Google Cloud should host and power the agent; GitLab should remain the surface where the judge sees the work happen.

## Honest risks
- **GitLab MCP is beta** and may have tier or environment constraints.
- **GitLab is still a crowded track**, so depth matters more than breadth.
- **Security credibility matters**: the blast-radius scoring must feel disciplined, not hand-wavy.
- **Too many repos will kill velocity**. Keep the demo world intentionally small but realistic.

## Best external resources
- [Hackathon resources](https://rapid-agent.devpost.com/resources)
- [GitLab MCP server docs](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/)
- [GitLab -> Google Cloud deployment guide](https://about.gitlab.com/blog/fast-and-secure-ai-agent-deployment-to-google-cloud-with-gitlab/)
- [Cloud Run MCP/agent codelab](https://codelabs.developers.google.com/codelabs/cloud-run/use-mcp-server-on-cloud-run-with-an-adk-agent)

## Bottom line
If we submit on GitLab, **security response beats onboarding**. It is more urgent, more visual, more technical, and much easier for a judge to remember.

---

## Build status

The project is now a runnable submission scaffold:

```bash
cd agent
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
blast-radius-agent
```

Open `http://localhost:8080` for the dashboard, or:

```bash
curl -N -X POST http://localhost:8080/incidents/analyze \
  -H "Content-Type: application/json" \
  -d '{"cve_id":"CVE-2026-4242","vulnerable_package":"log4js","fixed_version":"6.9.1"}'
```

| Path | Purpose |
|---|---|
| `agent/` | Python backend + dashboard |
| `agent/data/` | Service catalog + runbooks (Agent Builder grounding) |
| `demo-script.md` | 3-minute video beats |
| `build-plan.md` | Day-by-day execution plan |
| `Dockerfile` | Cloud Run image |
| `.gitlab-ci.yml` | Test, scan, deploy pipeline |
| `SCAFFOLD-NOTES.md` | What's done vs. optional polish |
