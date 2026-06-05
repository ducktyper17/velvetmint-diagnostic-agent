# Blast Radius — 3-minute demo script

## Hook (0:00–0:15)
"When a critical package CVE lands, security teams spend hours figuring out which services matter. Blast Radius does it in minutes using Gemini, Google Cloud, and GitLab."

## Trigger (0:15–0:35)
- Open the hosted dashboard at `/`
- Show the default CVE: `CVE-2026-4242`, package `log4js`
- Click **Analyze blast radius**

## Agent reasoning (0:35–1:30)
- Point to the live stream:
  - service catalog + runbooks loaded
  - GitLab group scan
  - dependency inspection
  - risk ranking

## GitLab actions (1:30–2:15)
- Cut to GitLab (or stay on stream) showing:
  - incident issue created
  - patch MRs opened for affected services
  - security pipeline checks running
  - one safe auto-deploy to Cloud Run for the low-risk service

## Close (2:15–3:00)
- Read the executive summary:
  - 3 services affected
  - checkout-service highest risk
  - human approval required for tier0
- Tech stack slide:
  - Gemini on Vertex AI
  - Google Cloud Agent Builder grounding
  - Official GitLab MCP
  - GitLab CI/CD → Artifact Registry → Cloud Run
