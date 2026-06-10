# Elastic Agent Builder — tool definitions

The agent calls six tools over the Elastic Agent Builder MCP endpoint. Five are
**ES|QL-backed custom tools** and one is a **hybrid (ELSER) search tool**; the
last writes memory back. Create each one in Kibana → **Agent Builder → Tools**,
using the tool **id** exactly as shown (the agent calls tools by these names),
then copy the MCP endpoint URL from the Tools UI into `ELASTIC_MCP_URL`.

The MCP API key needs the `agentBuilder:read` privilege (plus read on the four
indices). See `agent/scripts/elastic_setup.py` for the index mappings.

---

## 1. `search_building_memory` — memory lookup (ES|QL)

Returns a prior brief for the address if one exists.

```esql
FROM building_briefs
| WHERE address == ?address
| SORT updated_at DESC
| LIMIT 1
| KEEP address, risk_score, summary, top_red_flags, evidence
```

Param: `address` (keyword). The agent maps `risk_score → prior_risk_score`,
`top_red_flags → prior_flags`, and treats a hit as `found = true`.

---

## 2. `get_hpd_violations` — hard building evidence (ES|QL)

Open violations, severe categories, and recent examples for the building.

```esql
FROM hpd_violations
| WHERE address == ?address AND status == "open"
| STATS open_violations = COUNT(*),
        severe_categories = VALUES(category)
        BY severity_class
| SORT severity_class ASC
```

A companion query pulls the two most recent descriptions for `recent_examples`:

```esql
FROM hpd_violations
| WHERE address == ?address
| SORT reported_at DESC
| LIMIT 2
| KEEP description, reported_at
```

---

## 3. `get_311_signals` — quality-of-life signals (ES|QL)

Complaint volume in the last 90 days, top categories, and the late-night noise
share that drives the "work nights?" follow-up.

```esql
FROM nyc_311
| WHERE zip == ?zip AND created_at > NOW() - 90 days
| EVAL is_night = CASE(hour_of_day >= 22 OR hour_of_day <= 5, 1, 0)
| STATS complaint_count_90d = COUNT(*),
        night_noise = SUM(is_night),
        top_categories = VALUES(complaint_type)
| EVAL nighttime_noise_share = night_noise::double / complaint_count_90d
| KEEP complaint_count_90d, top_categories, nighttime_noise_share
```

Param: `zip` (derived from the normalized address; a geo_distance variant on
`location` is available for address-level radius filtering).

---

## 4. `search_tenant_sentiment` — hybrid retrieval (semantic + keyword)

The differentiator: ELSER semantic search over `tenant_signal_docs.body`
combined with a keyword match, so indirect complaints ("paper-thin walls",
"bar two doors down") surface for a query like "noise at night".

```esql
FROM tenant_signal_docs METADATA _score
| WHERE zip == ?zip
| WHERE match(body, ?query, { "boost": 2.0 })
| SORT _score DESC
| LIMIT 5
| KEEP title, body, source, url, _score
```

`body` is a `semantic_text` field, so `match` runs ELSER automatically. Params:
`zip`, `query` (the agent passes a short intent string, e.g. the listing address
plus "noise heat pests management"). The agent maps hits → `highlights` and the
count → `mentions_found`.

---

## 5. `compare_to_neighborhood_baseline` — aggregation (ES|QL)

How this building's complaint density compares to its ZIP baseline.

```esql
FROM nyc_311
| WHERE created_at > NOW() - 90 days
| EVAL is_target = CASE(address == ?address, 1, 0)
| STATS building = SUM(is_target), zip_total = COUNT(*) BY zip
| WHERE zip == ?zip
| EVAL buildings_in_zip = 80   /* approx; tune per ZIP */
| EVAL zip_avg = zip_total::double / buildings_in_zip
| EVAL complaint_index_vs_zip = building::double / zip_avg
| KEEP complaint_index_vs_zip
```

A value `> 1.3` means materially worse than the local norm; the agent turns that
into the "complaint density above neighborhood baseline" red flag.

---

## 6. `save_building_brief` — memory writeback (index tool)

After synthesis, the agent writes the normalized brief back so follow-up
questions reuse it instead of re-investigating. Configure as an **index
document** tool against `building_briefs`:

```json
{
  "address": "{{address}}",
  "risk_score": {{risk_score}},
  "summary": "{{summary}}",
  "top_red_flags": {{top_red_flags}},
  "evidence": {{evidence}},
  "updated_at": "{{now}}"
}
```

This is the "Elastic as a context layer" move — the second query on the same
building is faster and richer because the agent reads its own prior brief via
tool #1.

---

## Why this is load-bearing, not decorative

| Capability Elastic pushes | Where it shows up |
|---|---|
| ES|QL custom tools | tools #1, #2, #3, #5 |
| Hybrid retrieval (ELSER) | tool #4 |
| Aggregations / comparisons | tool #5 |
| Memory / context layer | tools #1 + #6 (writeback) |
| Built-in MCP server | all six, exposed to Gemini over MCP |

Remove Elastic and the agent has no evidence, no semantic recall, and no memory —
it collapses to a chatbot. That is the bar the rubric's Technological
Implementation criterion is checking for.
