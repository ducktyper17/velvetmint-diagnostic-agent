# Scaffold status — Blast Radius

## Done
- FastAPI backend with SSE incident stream
- Deterministic blast-radius scoring over a 5-service demo catalog
- GitLab MCP HTTP client with demo fallback
- Gemini executive summary (Vertex AI via `google-genai`)
- Grounding docs in `agent/data/` (Agent Builder data-store parity)
- Static dashboard at `/`
- Dockerfile + GitLab CI/CD pipeline skeleton
- Unit tests for health, scenario ranking, and incident loop

## Still optional before submit
- Wire live GitLab MCP OAuth in a real GitLab.com group
- Replace demo catalog with real group projects
- Persist incidents for replay (`GET /incidents/{id}`)
- Record final YouTube/Vimeo demo video
- Host on Cloud Run with public URL for judging window

## Hackathon compliance checklist
- [x] Gemini on Google Cloud (Vertex AI)
- [x] Partner MCP integration surface (GitLab)
- [x] No non-Google AI in agent path
- [x] OSI license at repo root (Apache-2.0 via pyproject)
- [ ] Public hosted URL during judging
- [ ] ≤3 minute demo video on YouTube/Vimeo
