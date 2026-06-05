# Setup Checklist — Self-Improving QA Agent

Pre-submission checklist for the **Google Cloud Rapid Agent Hackathon
(Arize Phoenix track)**. Submission deadline: **June 11, 2026**. Internal
target: submit at least 48h early.

Work through these steps top-to-bottom. Each step has a verification
command and an expected output so you can confirm it landed.

---

## 1. Phoenix Cloud account + API key

1.1. Sign up for Phoenix Cloud at <https://app.phoenix.arize.com>.

1.2. Create a workspace (the URL path will become `/s/<your-space>`).

1.3. Generate a Phoenix API key in *Settings → API Keys*. It looks like
`px_live_xxxxxxxxxxxxxxxx`.

**Verify:**

```bash
# Replace placeholders. This should print "200" if the key is valid.
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer ${PHOENIX_API_KEY}" \
  "${PHOENIX_COLLECTOR_ENDPOINT}/v1/projects"
```

**Expected:** `200`. A `401` means the key is wrong; a `404` almost always
means `PHOENIX_COLLECTOR_ENDPOINT` is missing the `/s/<space>` path
segment (see step 2).

---

## 2. Phoenix endpoint — *gotcha alert*

The `PHOENIX_COLLECTOR_ENDPOINT` env var **must include the
`/s/<your-space>` path segment**. The dashboard URL gives you the right
prefix; copy from there.

- **Correct:** `https://app.phoenix.arize.com/s/your-space-name`
- **Wrong (will silently fail with empty datasets):** `https://app.phoenix.arize.com`

This is the single most common breakage. If `make seed` succeeds but the
seeded objects don't appear in the UI, this is why.

**Verify:**

```bash
echo "$PHOENIX_COLLECTOR_ENDPOINT" | grep -E '/s/[a-zA-Z0-9_-]+$' \
  && echo "ok: endpoint includes /s/<space>" \
  || echo "MISSING /s/<space> — fix before continuing"
```

**Expected:** `ok: endpoint includes /s/<space>`.

---

## 3. GCP project + Vertex AI + ADC

3.1. Create or pick a GCP project. Note the project id; you'll export it
as `GOOGLE_CLOUD_PROJECT`.

3.2. Enable APIs (one-shot):

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  --project "$GOOGLE_CLOUD_PROJECT"
```

3.3. Authenticate Application Default Credentials:

```bash
gcloud auth application-default login
gcloud config set project "$GOOGLE_CLOUD_PROJECT"
```

3.4. Pick a region (`us-central1` is the default in `scripts/deploy.sh`).

**Verify:**

```bash
gcloud ai models list --region=us-central1 --project="$GOOGLE_CLOUD_PROJECT" --limit=1 \
  && echo "ok: Vertex AI reachable"
```

**Expected:** the command succeeds (any output, including empty) — no
`PERMISSION_DENIED` or `API has not been used`.

---

## 4. Local `.env`

4.1. Copy the template and fill in the four required values:

```bash
cd 02-arize-mystery-shopper/agent
cp .env.example .env
# edit .env, set:
#   PHOENIX_API_KEY=px_live_...
#   PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/<your-space>
#   GOOGLE_CLOUD_PROJECT=<your-gcp-project-id>
#   GOOGLE_CLOUD_LOCATION=us-central1
```

**Verify:**

```bash
grep -E '^(PHOENIX_API_KEY|PHOENIX_COLLECTOR_ENDPOINT|GOOGLE_CLOUD_PROJECT|GOOGLE_CLOUD_LOCATION)=' \
  02-arize-mystery-shopper/agent/.env
```

**Expected:** four non-empty lines.

---

## 5. Local end-to-end smoke

5.1. Install Python deps with `uv` (3.11 / 3.12; matches the Arize
reference repo).

5.2. Run the three-step smoke sequence:

```bash
cd 02-arize-mystery-shopper/agent
make setup       # uv sync
make seed        # pushes judge prompts + scenarios + SUT seed prompt into Phoenix
make run-loop    # runs the deterministic six-phase loop end-to-end
```

**Verify (`make setup`):**

**Expected:** `uv sync` finishes with `Resolved N packages` and no
`error:` lines.

**Verify (`make seed`):**

**Expected:** three sections of `upsert ok` lines for the six judge
prompts, one `dataset upload ok: velvetmint-support.scenarios`, and one
`upsert ok: sut-velvetmint-support`.

**Verify (`make run-loop`):**

**Expected:** three JSON files written to `agent/out/`:
`baseline.json`, `post_fix.json`, `delta_report.json`. The
`delta_report.json` should show a positive delta on at least one
dimension (typically `hallucination`).

---

## 6. Phoenix UI sanity check

Open `https://app.phoenix.arize.com/s/<your-space>` in a browser. You
should see:

- A **project** named `self-improving-qa-agent` with traces.
- A **dataset** named `velvetmint-support.scenarios` with 30 examples.
- Six **prompts** under the names `judge.empathy.v1`, `judge.accuracy.v1`,
  etc.
- A **prompt** named `sut-velvetmint-support` with at least 1 version.

If any are missing: re-run `make seed`. The seed script is idempotent and
prints WARN lines on any per-object failure.

---

## 7. Secret Manager + Cloud Run deploy

7.1. Push the Phoenix API key into Secret Manager:

```bash
printf '%s' "$PHOENIX_API_KEY" \
  | gcloud secrets create phoenix-api-key \
      --project "$GOOGLE_CLOUD_PROJECT" \
      --data-file=-
# If it already exists, replace `create` with: versions add phoenix-api-key
```

**Verify:**

```bash
gcloud secrets versions access latest --secret=phoenix-api-key \
  --project="$GOOGLE_CLOUD_PROJECT" \
  | head -c 8
```

**Expected:** `px_live_`.

7.2. Deploy backend + frontend in one shot:

```bash
cd 02-arize-mystery-shopper/agent
make deploy
```

**Verify:**

```bash
gcloud run services list \
  --region us-central1 \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --filter='metadata.name~self-improving-qa-' \
  --format='table(metadata.name,status.url)'
```

**Expected:** two services, `self-improving-qa-backend` and
`self-improving-qa-frontend`, both with public URLs.

7.3. Hit the backend health surface:

```bash
curl -s "${BACKEND_URL}/healthz" | head -c 200
```

**Expected:** a `200` response with a small JSON body. (If `/healthz` is
not wired, hit the FastAPI docs at `${BACKEND_URL}/docs` instead and
confirm a 200.)

---

## 8. Record the demo video

8.1. Record at 1920x1080, ≤ 3 minutes. Follow `VIDEO_SCRIPT.md`
beat-by-beat.

8.2. Upload to YouTube as **unlisted** (not private — judges need the
URL).

8.3. Title format: *"Self-Improving QA Agent — Google Cloud Rapid Agent
Hackathon (Arize Phoenix)"*

**Verify:**

- Open the unlisted URL in an incognito window and confirm playback works
  end-to-end.
- Confirm the video is **3:00 or under**. Devpost cuts off over-length
  videos silently.

---

## 9. Devpost submission

9.1. Open <https://rapid-agent.devpost.com/> and start a new submission.

9.2. Copy each section from `DEVPOST_DRAFT.md`:
   *Inspiration*, *What it does*, *How we built it*, *Challenges*,
   *Accomplishments*, *What we learned*, *What's next*, *Built with*,
   *Try it out*. Replace the four placeholder URLs in the *Try it out*
   section with the real Cloud Run + Phoenix + YouTube + GitHub URLs.

9.3. Set the track to **Arize Phoenix**.

9.4. Attach the public GitHub repo URL. Confirm Apache-2.0 LICENSE is at
the workspace root (it is — `/Users/<you>/.../google hackathon/LICENSE`).

9.5. Submit. Confirm you see a green "Submitted" badge.

**Verify:**

- Devpost shows your submission with a "Submitted" badge.
- The video plays inside the Devpost embed.
- The repo URL resolves and shows the Apache-2.0 license on the public
  GitHub page.

---

## Pre-submission punch list

Tick all of these before hitting Submit:

- [ ] `PHOENIX_COLLECTOR_ENDPOINT` includes `/s/<space>` (step 2)
- [ ] `make seed` is green (step 5)
- [ ] `make run-loop` writes a positive-delta `delta_report.json` (step 5)
- [ ] Cloud Run services have public URLs (step 7)
- [ ] Demo video is unlisted, ≤ 3:00, plays in incognito (step 8)
- [ ] LICENSE (Apache-2.0) is at the workspace root
- [ ] Devpost track set to **Arize Phoenix**
- [ ] All four placeholder URLs in `DEVPOST_DRAFT.md` replaced with real
      URLs before paste

Once all eight boxes are checked: submit.
