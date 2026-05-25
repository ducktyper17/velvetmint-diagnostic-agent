# Legal disclaimer — exact text, non-negotiable

> This file contains the **literal disclaimer strings** that ship in the
> Doctor's Note Decoder product, in the demo video, on the landing page,
> and in every API response. They are reproduced here, in one place, so
> any change has to be a deliberate edit to this file. The agent's
> system prompt loads these strings verbatim from `agent/prompts.py`,
> which loads them from here at build time.
>
> If you are reviewing this project: this file is the most important
> file in the repository. A medical-information product that misframes
> itself as diagnostic is not just a UX problem — it is a patient-safety
> problem and a regulatory one. Read this file before you read the code.

---

## Plain-English statement (used on the landing page and at the top of every response)

> **This tool does not diagnose. It explains.**
>
> Doctor's Note Decoder reads the words on your medical report and the
> publicly available medical literature about those words, and produces
> a plain-language explanation plus questions to ask your doctor. It is
> not a substitute for a clinician. It does not know your full medical
> history. It cannot examine you. It cannot order tests. It is not a
> medical device.
>
> If you are experiencing a medical emergency, call your local emergency
> number. If you are worried about a result, contact the clinician who
> ordered the test.

This string is referenced in code as `DISCLAIMER_PLAIN`.

## Long-form disclaimer (returned in every `/decode` response, attached to every saved vault entry, and included as a footer in any exported PDF)

> **Important: please read before using this explanation.**
>
> 1. **Not a diagnosis.** This explanation does not tell you what
>    medical condition you have, do not have, or are at risk of. Only a
>    licensed clinician who has access to your full history and can
>    examine you can do that.
>
> 2. **Not a substitute for medical advice.** Do not start, stop, delay,
>    or change any treatment, test, appointment, or medication based on
>    this explanation. If this explanation appears to disagree with what
>    a clinician has told you, the clinician is the source of record.
>
> 3. **Not a medical device.** Doctor's Note Decoder is an information
>    tool. It has not been reviewed or cleared by the U.S. Food and Drug
>    Administration, by Health Canada, by the European Medicines Agency,
>    by the U.K. Medicines and Healthcare products Regulatory Agency, or
>    by any other regulator. It is not certified to the IEC 62304 or
>    ISO 13485 standards. It does not have a CE mark.
>
> 4. **Not HIPAA-covered in this form.** The demo deployment is not
>    operated under a Business Associate Agreement. Do not upload
>    documents containing protected health information for anyone other
>    than yourself, and only if you accept that the demo infrastructure
>    is not a HIPAA-compliant environment. A production deployment would
>    require BAAs with the underlying cloud and database providers and
>    is out of scope for this hackathon submission.
>
> 5. **The literature it cites is general, not personal.** The
>    statistics surfaced (e.g. "roughly X in 100 cases of this finding
>    are Y") describe the published population, not you. The published
>    population may not match your age, sex, ancestry, comorbidities,
>    family history, or local clinical practice.
>
> 6. **The AI can be wrong.** The extraction step may misread terms.
>    The retrieval step may surface a non-representative paper. The
>    synthesis step may phrase something in a way a clinician would
>    nuance differently. Treat every sentence here as a starting point
>    for a conversation with your clinician, not as the final word.
>
> 7. **In an emergency, do not use this tool.** Call your local
>    emergency number. Examples (this list is not exhaustive): chest
>    pain, difficulty breathing, severe bleeding, sudden weakness on
>    one side, sudden severe headache, suicidal thoughts, signs of
>    stroke, signs of anaphylaxis, or a child who is unresponsive.
>
> By using Doctor's Note Decoder you acknowledge that you have read and
> understood this disclaimer.

This string is referenced in code as `DISCLAIMER_LONG`.

## In-response phrasing rules (enforced by the system prompt and the response schema)

These are the linguistic rules the agent must follow in *every* response.
They exist so the disclaimer is not just a footer that users skip but is
reinforced by the actual prose:

1. The agent **never** writes "you have…", "you do not have…",
   "you probably have…", "this is…", or "this is not…" about a medical
   condition. It writes "your report describes…",
   "your report's terminology refers to…",
   "in published series, this finding is associated with…".
2. The agent **never** writes "the diagnosis is…" or "the diagnosis
   could be…". It writes "your report's recommendation is…" and
   "questions to ask the clinician include…".
3. The agent **never** writes "you should…" about a clinical action.
   It writes "you may want to ask your clinician whether…".
4. The agent **always** ends the structured response with the
   `disclaimer` field populated by `DISCLAIMER_LONG` verbatim. If the
   field is empty for any reason, the API returns HTTP 500.
5. The agent **always** surfaces a follow-up suggestion that includes
   the phrase *"with your clinician"* (this is enforced by a
   post-generation check in `responder.py`).
6. The agent **never** generates dosing, drug-selection, or
   intervention recommendations even when asked. The polite refusal
   string is `REFUSAL_OUT_OF_SCOPE`.

## Standard refusal string (`REFUSAL_OUT_OF_SCOPE`)

> I can explain what your report says and surface relevant published
> literature, but I am not the right tool to recommend a specific
> treatment, medication, dose, or course of action. Those decisions
> belong with your clinician, who knows your full history and can
> examine you. If you want, I can suggest questions you could ask them
> at your appointment.

## Standard refusal string for emergency-shaped inputs (`REFUSAL_EMERGENCY`)

> What you are describing may need urgent in-person attention. Please
> contact your local emergency number or go to your nearest emergency
> department. I am an information tool and I am not appropriate for
> emergencies.

## Scope of data we will and will not seed into the knowledge base

The seed data in `agent/seed_data.py` is illustrative only. For any real
deployment:

- **In scope to seed:** PubMed abstracts (titles + abstracts are
  available under NLM's terms of use for non-commercial research,
  re-check at productization), public clinical guidelines that permit
  excerpting (ACR TIRADS, NCCN where licensed, ESMO open chapters),
  and *consented, de-identified* patient experiences. Forum content
  must be excerpted under the source's terms of service or explicit
  consent from posters; the demo uses fabricated forum-style entries
  that are clearly labeled as such in `seed_data.py`.
- **Out of scope to seed:** full-text journal articles behind paywalls,
  Up-to-date / DynaMed content, Epic / MyChart screenshots, any real
  patient data, anything where the licensing is not explicit.

## Audit trail

| Date | Change | By |
|---|---|---|
| 2026-05-23 | Initial version. Aligned with the backup scaffold. | Hackathon team |

Any future change to the disclaimer text below the audit table must add
a new row here, including a one-line rationale.
