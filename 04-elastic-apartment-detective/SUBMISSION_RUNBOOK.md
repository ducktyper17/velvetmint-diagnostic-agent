# Apartment Detective — Submission Runbook

Everything you need to record the video and submit. Code is built, tested, and
pushed. This is the operational checklist.

Time budget: ~45 min total (10 start app · 15 record · 5 upload · 15 Devpost).

---

## PART A — Start the app locally (≈10 min)

You need **two terminals**. The backend on port 8095, the frontend on 3001.
(Port 8080 is taken by another agent on this machine — that's why we use 8095.)

### Terminal 1 — backend
```bash
cd "/Users/saaksshi17/Desktop/Vibe coding 101/google hackathon/04-elastic-apartment-detective/agent"
./.venv/bin/uvicorn agent.main:app --port 8095
```
Wait for: `Application startup complete.` Leave this terminal running.

> First time only (if `.venv` is missing):
> `python3.11 -m venv .venv && ./.venv/bin/pip install -e ".[dev]" && cp .env.example .env`

### Terminal 2 — frontend
```bash
cd "/Users/saaksshi17/Desktop/Vibe coding 101/google hackathon/04-elastic-apartment-detective/frontend"
BACKEND_URL=http://localhost:8095 npx next dev -p 3001
```
Wait for: `✓ Ready`. Leave this terminal running too.

> First time only (if `node_modules` is missing): run `npm install` first.

### Confirm it works
Open **http://localhost:3001** in Chrome. You should see the dark "Apartment
Detective" dashboard, the listing URL prefilled, and a **replay** checkbox
(checked) beside the Investigate button.

Sanity check before recording: click **Investigate** once. In ~11 seconds you
should see five tool calls stream, the evidence strip fill (5 violations / 18
complaints / 61% / 1.7×), and a **9.8/10 — high confidence** brief. If that
works, you're ready.

---

## PART B — Record the video (≈15 min)

Two options. **Option 1 is the safe, fast one.**

### Setup (both options)
1. In Chrome, go to **http://localhost:3001**. Press **Cmd+Ctrl+F** for full screen.
2. Make sure the **replay** checkbox is **CHECKED** (default). This paces the demo so it's readable on camera.
3. Confirm the listing URL field shows the `123-orchard-st` link.
4. Open the macOS recorder: **Cmd+Shift+5** → **Record Entire Screen** (or "Record Selected Portion" and drag a 16:9 box) → **Options → Microphone → MacBook Microphone** if narrating live.

### Option 1 — One take, narrate live (simplest)
Press **Record**, then:

| # | Click / action | What happens | Say (optional) |
|---|---|---|---|
| 1 | Pause 2s on the idle dashboard | — | "Apartment listings are written to make you sign. They don't show you the public record. This does." |
| 2 | Click **Investigate** (top-right) | Five tool calls stream with ES\|QL / hybrid / memory badges; evidence strip fills | "Five Elastic tools in one parallel turn — HPD violations, 311 complaints, a hybrid semantic search, a neighborhood comparison." |
| 3 | Let the **evidence strip** finish (four tiles) | 5 violations · 18 complaints · 61% late-night · 1.7× | "Here's what the listing hid. Five open violations. Sixty-one percent of nearby noise is after midnight." |
| 4 | Point at the **risk brief** (right side) | 9.8/10 dial + green **high confidence** chip + red flags + evidence + questions | "A 9.8 risk score — high confidence, because five independent public sources agree. Plus the questions to ask the landlord." |
| 5 | Click the **Ask a follow-up** box (bottom-right), type **What's the biggest concern if I work nights?**, press **Enter** | A fast answer streams; `search_building_memory` returns found, only 2 tools run | "And the payoff — it doesn't re-investigate. It reads its own saved brief back from Elastic and answers from memory. That's the context layer." |
| 6 | Pause 2s | — | "Apartment Detective. Get the truth before you sign." |

Stop with the menu-bar stop icon (or **Cmd+Ctrl+Esc**). Keep it **under 3:00** — aim for ~2:30.

### Option 2 — Polished (record silent, add VO + title cards after)
Same clicks with replay on, no narration. Then in iMovie/CapCut: add a title
card at the start, record voice-over following **`VIDEO_SCRIPT.md`** (it has
exact beat timings), add a closing card with your GitHub + hosted URL. Keep
total **≤ 3:00**.

### Recording tips
- If a take is too fast/slow, uncheck and recheck replay, then click Investigate again — it's identical every run.
- Auto-hide the dock (System Settings → Desktop & Dock → Automatically hide and show the Dock).
- Record at native resolution; 1080p minimum.

---

## PART C — Upload the video (≈5 min)
1. **youtube.com → Create → Upload video**. Drag your recording in.
2. Title: **Apartment Detective — Gemini + Elastic renter due-diligence agent**.
3. Visibility: **Unlisted** (NOT Private — judges must watch without signing in).
4. Copy the share link once processing finishes.

---

## PART D — Make the repo public (≈2 min)
1. github.com → repo **velvetmint-diagnostic-agent** → **Settings**.
2. **Danger Zone → Change repository visibility → Make public**. Confirm.
3. Your code link for the submission:
   `https://github.com/ducktyper17/velvetmint-diagnostic-agent/tree/mongodb-doctors-note-runnable/04-elastic-apartment-detective`

---

## PART E — Fill the Devpost submission (≈15 min)
**rapid-agent.devpost.com → Submit a project.** Fill each field:

| Field | What to put |
|---|---|
| Project name | **Apartment Detective** |
| Tagline | **Paste a listing. Get the truth before you sign.** |
| Description | Paste the body of **`DEVPOST_DRAFT.md`** (Inspiration → What it does → How we built it → Challenges → Built with). |
| Built with (tags) | `gemini` `vertex-ai` `google-cloud-run` `elastic` `elasticsearch` `nextjs` `fastapi` `python` `typescript` `server-sent-events` |
| Video demo link | Your YouTube **unlisted** URL (Part C) |
| GitHub / code repo | The tree URL from Part D |
| Try it out / links | Repo URL (+ hosted Cloud Run URL if you deploy — optional) |
| Partner track | **Elastic** |
| Images | 2–3 screenshots: the streaming investigation, the evidence strip, the 9.8 brief. |

Then click **Submit**.

---

## PART F — Final pre-submit checklist
- [ ] GitHub repo is **Public**
- [ ] YouTube video is **Unlisted** (not Private) and **≤ 3:00**
- [ ] Description pasted from `DEVPOST_DRAFT.md`
- [ ] Partner track set to **Elastic**
- [ ] Video + repo links both work in an **incognito** window
- [ ] Submitted before the deadline

---

## Optional: go live for a higher Tech score (≈60 min)
The demo above runs offline (seeded data, deterministic planner) — valid and
complete. To show real Elastic + Gemini running (strengthens the "Technological
Implementation" score), do **`SETUP_CHECKLIST.md` Path B** (Elastic Serverless +
the 6 Agent Builder tools + Vertex access), set `DEMO_MODE=false` and
`STUB_GEMINI_RESPONSES=false`, **uncheck replay** in the UI, and record against
the live run. `./scripts/deploy.sh all` gives a hosted URL for "Try it out."
