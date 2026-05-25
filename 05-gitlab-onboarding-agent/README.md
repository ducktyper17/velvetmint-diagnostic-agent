# Track 5: GitLab — Engineering Onboarding Agent (one-pager)

> **This is a pivot backup, not a primary build.** GitLab track is the most crowded — submitting here is high risk regardless of idea quality.

## One-liner
*"Day 1 → productive by Friday."* — When a new engineer joins, the agent reads the team's GitLab project history (issues, MRs, wiki, incidents), then creates a personal "Week 1" project for the new hire: 5 first-issue tasks that each touch a system they'll own, the right mentor assignments, a curated wiki reading list, and calendar invites with the relevant people.

## Why GitLab
The agent does **real work in GitLab**, not just code review. It creates issues, opens MRs, writes wiki pages, runs pipelines — across multiple resource types. That breadth is what makes a GitLab judge sit up: most submissions will use 2 tools (read issue, comment on MR). We'll use 10+.

## Partner integration points
GitLab MCP server (official, GitLab 18.6+) used in WRITE mode:
- `create_issue` (multiple — the "first 5" for the new hire)
- `update_issue` (assign mentors via reviewer)
- `add_issue_comment` (welcome notes from the agent)
- `get_merge_request_changes` (analyze recent code for context)
- `list_pipelines` (find a successful build to base "Hello World" on)
- `gitlab_analyze` meta-tool (LLM-assisted technical-debt detection on suggested first-issues)

Plus wiki write access via community MCP (e.g., `jmrplens/gitlab-mcp-server`).

## Architecture (rough)
```
Trigger: webhook from "new engineer added to GitLab group"
  → Cloud Function invokes the agent
  → Agent Builder + Gemini 3:
     1. Read team project (repos, recent MRs, recent incidents)
     2. Read team wiki (architecture pages, runbooks)
     3. Classify the engineer's role from the invitation metadata
     4. Identify 5 issues that match their role + are well-scoped
     5. Identify 3 senior engineers as mentors (from MR reviewer history)
     6. Create new personal project for the engineer
     7. Open 5 issues, assigned to engineer, with mentor as reviewer
     8. Generate a wiki "Week 1" page
     9. Send a Slack message + calendar invites
Output: GitLab project + structured "Week 1 plan" doc
```

## Demo flow (3 min)
- 0:00–0:15: Hook — "Onboarding takes 2-4 weeks. With this agent, day 5."
- 0:15–0:30: Show the agent receiving a "new hire" webhook
- 0:30–2:15: Stream reasoning + actions. Cuts to GitLab UI showing issues appearing, wiki page being written, MR with starter changes opening, Slack messages being sent
- 2:15–2:45: Cut to the new hire's view — a clean GitLab project page with their first week mapped out
- 2:45–3:00: Tagline + tech stack

## Why this is our backup, not primary
- **GitLab track is the most crowded** (10K+ registrants, GitLab is everyone's default)
- **The agent's reasoning is less visible** — it's mostly creating things; the "thinking" moments are quieter
- **Faking a believable team in 19 days is hard** — needs realistic past MRs, incidents, wiki

## When to pivot to this
- If we get access to a real team's GitLab and can use it (with permission)
- If we want a story that's pure agent autonomy with minimal data dependencies

## Estimated build effort
- 4 days realistic "fake team" setup in GitLab
- 7 days agent build + actions across resources
- 4 days polish + video
- 4 days buffer

Doable in 19 days.

## Honest weakness
Onboarding is a known problem with many existing tools (Trainual, Notion templates, internal scripts). The agent angle differentiates, but the underlying job ("write an onboarding plan") could feel familiar to judges.
