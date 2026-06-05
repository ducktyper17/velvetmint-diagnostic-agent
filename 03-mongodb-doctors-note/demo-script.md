# Demo video script — 3 minutes

> Target length: 2:50–3:00. Hackathon allows up to 3:00 and judges
> watch many in a row, so we end at 2:55 and leave 5 seconds of clean
> outro. Every beat below has a target duration; the sum is 2:55.

## Working title for the upload

> "Doctor's Note Decoder — stop Googling your medical results at 2am."

## Cast and assets

- **Voiceover** — one narrator, calm, slightly tired (the patient voice,
  not the doctor voice). Recorded separately, mixed under screen capture.
- **On-screen patient persona** — Priya, 41 (fictional). We do not show
  a face; we show a phone and a laptop on a kitchen counter.
- **The report** — a fictional thyroid ultrasound report we wrote
  ourselves, clearly labeled `SAMPLE_REPORT — NOT A REAL PATIENT` in the
  footer of the PDF. The footer is not visible on screen but exists so
  any frame grab is unambiguous.
- **Disclaimer overlay** — bottom-of-frame band that reads
  *"Demo only. Not medical advice. Not diagnostic."* visible for the
  entire video.

## Beats

### 0:00–0:15 — Cold open, the 2am moment (15s)

Visual: phone on a kitchen counter, dark room, MyChart-style notification
glow. Cut to the report PDF on a laptop. The camera lingers on the line
*"TIRADS 3 nodule, 2.1 cm, mixed echogenicity"* with the rest blurred.

VO: *"It is 11pm. Your portal pings. You open the report. You have no
idea what any of it means. Your appointment is in nine days. So you do
what everyone does — you Google it. And Google shows you cancer."*

### 0:15–0:30 — The problem framing (15s)

Visual: split screen. Left: Google search results for "TIRADS 3" with
worst-case headlines highlighted. Right: a generic chatbot confidently
saying *"You likely have..."* with a red X drawn over it.

VO: *"Search engines show you the worst case because that is what gets
clicks. Chatbots will diagnose you, which is exactly what they should
not do. Neither tells you the actual statistics for your specific
finding."*

### 0:30–0:45 — Introduce the agent (15s)

Visual: clean web page, single upload area. Title:
*"Doctor's Note Decoder."* Subtitle:
*"We explain what your report says. We do not diagnose."*

VO: *"Doctor's Note Decoder reads your report, reads the medical
literature, and tells you what your report says in plain English — and
gives you three specific questions to ask your doctor. It does not
diagnose. It explains."*

### 0:45–1:05 — Upload and extraction (20s)

Visual: the sample thyroid ultrasound PDF is dragged into the upload
area. Spinner. Then a panel slides in titled
*"What the report says (extracted, not interpreted)."* It shows:

```
Modality:        Ultrasound, thyroid
Finding:         Nodule, right lobe, 2.1 cm
Classification:  TIRADS 3
Features:        Mixed echogenicity; no microcalcifications
Recommendation:  Follow-up ultrasound in 12 months
```

VO: *"Gemini 3 reads the PDF as written — no rewording, no
interpretation. It pulls out the actual medical entities so we know what
to look up."*

### 1:05–1:35 — The hybrid retrieval, visually (30s)

Visual: a live-streamed reasoning panel on the right. Three tabs animate
into existence as the agent queries them:

```
Searching literature...        (12 PubMed abstracts)
Searching guidelines...        (ACR TIRADS 2017, ATA 2015)
Searching patient experiences...(8 de-identified forum excerpts)
```

Each tab shows the top three hits with snippets and a similarity score.
A small subtitle reads *"MongoDB Atlas Vector Search via the official
MongoDB MCP server."*

VO: *"The agent runs a hybrid search against a MongoDB Atlas knowledge
base — PubMed abstracts, clinical guidelines, and de-identified patient
experiences. Vector search for meaning, structured filters for
condition, severity, and recency, all in one Atlas aggregation pipeline.
Embeddings come from Google Cloud Vertex AI, and Atlas does the
retrieval through the official MongoDB MCP server."*

### 1:35–2:20 — The output card (45s, the hero moment)

Visual: a single clean card slides in. Four sections, each one revealed
as the narrator reads it.

```
TRANSLATION
Your report describes a 2.1 cm nodule in the right lobe of your thyroid.
"TIRADS 3" is the radiologist's standardized score for how suspicious
the nodule looks on ultrasound. TIRADS 3 means "mildly suspicious."

WHAT THIS MEANS
The radiologist's recommendation — follow-up ultrasound in 12 months —
is the standard recommendation for TIRADS 3 nodules of this size under
the ACR 2017 guideline. A 12-month follow-up means they expect to watch
it, not treat it.

STATISTICAL CONTEXT
Across published series, roughly 5 in 100 TIRADS 3 nodules of this size
turn out to be malignant on biopsy. The other 95 are benign. Biopsy is
not standardly performed for TIRADS 3 nodules under 2.5 cm unless other
features change.

THREE QUESTIONS TO ASK YOUR DOCTOR
1. "Should we baseline labs (TSH, free T4) before the follow-up scan?"
2. "If the nodule grows by the 12-month scan, what is the next step?"
3. "Are there features in the scan that change the 12-month timeline?"
```

Below the card, a quiet disclaimer panel:

```
This is an explanation of your report, not a diagnosis. It is not a
substitute for medical advice. Your doctor knows your full history.
```

VO: *"The translation. What it means. The actual base rate — not the
worst case. And three specific questions to ask the doctor — not vague
ones, the specific ones the literature suggests."*

### 2:20–2:40 — The MongoDB and GCP money shot (20s)

Visual: cut to a stack-overlay screen. Three logos stacked: Gemini 3,
MongoDB Atlas, Vertex AI. Below them, a code snippet of the actual
`$vectorSearch` aggregation we sent. Subtitle: *"One Atlas query.
Vector recall plus structured pre-filters plus recency reranking."*

VO: *"The whole thing is one MongoDB aggregation pipeline — vector
recall, structured pre-filters, and recency reranking, all in one
query. That is the right primitive for medical retrieval, and Atlas
gives it to you natively."*

### 2:40–2:55 — Close (15s)

Visual: return to the upload page. The disclaimer band brightens.

VO: *"Doctor's Note Decoder. We do not diagnose. We explain. So you can
walk into your appointment informed instead of terrified."*

Final frame: project name, GitHub repo URL, hackathon tag, the words
*"Built on Google Cloud Agent Builder, Gemini 3, Vertex AI, and MongoDB
Atlas."*

## Hard rules during recording

- The word *"diagnosis"* is **never** spoken as something the agent
  does. The narrator may say *"does not diagnose"* but never *"diagnoses
  you"*.
- The disclaimer band stays on for the entire video.
- The sample report shown on screen never reads as a real person — name
  fields are `Sample Patient`, MRN is `SAMPLE-0001`, DOB is the year
  `0001`.
- We never imply the user should skip a clinician. The closing line
  ends on *"walk into your appointment informed"* — i.e. the
  appointment still happens.

## Post-production checklist

- [ ] Lower-third badge: *"Demo. Not medical advice. Not diagnostic."*
      visible from 0:00 to 2:55.
- [ ] Closing card includes the GitHub repo URL and the project name.
- [ ] Audio levels: VO at -16 LUFS, background music (if any) at -32 LUFS.
- [ ] Export 1080p MP4 under 200 MB for Devpost upload.
- [ ] Upload to YouTube unlisted as a backup mirror.
