# Lovable Prompt — BrainVC Frontend

Paste the prompt below into Lovable. When it looks right, **export the code**
(GitHub or download) into `frontend/` and we run it locally with `npm run dev`
— everything stays on this machine, no mixed-content/CORS issues (the API
already allows all origins).

---

Build **BrainVC — The VC Brain**, an investor-grade dashboard for an AI venture
fund. Clean, minimal, Notion-level approachability with Bloomberg-level data
density. Light theme, generous whitespace, monospace for numbers. React +
TypeScript + Tailwind. API base: `http://localhost:8000/api` (plain fetch; CORS
is open; no auth).

**Core design rule: the three axis scores (founder, market, idea_vs_market)
are NEVER merged into one number.** Always show three separate cards/rows with
each score, its confidence band, and trend.

**Trust badge component** (used everywhere): pill showing trust level —
high=green, medium=amber, low=gray, flagged=red with a ⚠ icon. Tooltip shows
trust value (0–1), rationale, and verification method.

## Screens

### 1. Pipeline (home) — `GET /pipeline/ranked`
Returns `{thesis, opportunities: [{opportunity_id, company_name, track, status,
axes: {founder: {score, band: [lo,hi], trend, stance}, market: {...},
idea_vs_market: {...}}, ordering_key, recommendation}]}`.
Table of opportunities: company, track badge (inbound/outbound), status chip,
three mini axis meters (score + band drawn as a range bar + trend arrow), and
recommendation chip (invest_100k=green "INVEST $100K", escalate_to_human=amber
"ESCALATE", pass=gray). Small footnote: "ordering is thesis-weighted; axes are
never averaged". Header shows active thesis name with link to Thesis panel.

### 2. Opportunity detail — `GET /opportunities/{id}`, `GET /opportunities/{id}/scores`, `GET /opportunities/{id}/claims`, `GET /opportunities/{id}/trace`
Three large axis cards (score, confidence band as a horizontal range bar with
the basis string underneath in small text, trend, market stance where present,
rationale). Below: claims table (category, text, status, TrustBadge) — clicking
a claim opens a right drawer with its evidence links: for each, relation
(asserts/supports/contradicts), verbatim excerpt, source_ref (clickable when a
URL), source_type tag (deck_slide / github / web / …), retrieved_at. A "Trace"
tab lists the pipeline log entries (module, step, summary, model, timestamp) as
a vertical timeline. Buttons: "Run full pipeline" → `POST /opportunities/{id}/run`
(show staged progress from the returned timeline), "View memo".

### 3. Memo — `GET /opportunities/{id}/memo`
Returns `{memo: {recommendation, recommendation_rationale, sections: [{kind,
markdown}], gaps: [...], claim_ids}, claims: {uuid: claim}}`. Big recommendation
banner + rationale. Render each section's markdown; replace inline tokens
`[claim:UUID]` with a small numbered chip carrying that claim's TrustBadge
color — clicking opens the claim + evidence drawer (same as screen 2). Gaps
render as an amber "Declared gaps — not fabricated" list. This screen is the
trust centerpiece: every number visibly traces to a source.

### 4. Founders (outbound pool) — `GET /founders`
Cards: name, GitHub handle, evidence count, Founder Score (big number) with
band, and a sparkline of score_history (score over time). "Scan founder" form
at top: GitHub handle input → `POST /outbound/scan {github_handle}` (show the
returned cold_start: 5 dimension bars with rationales + known_unknowns list —
render unknowns prominently as "What we could NOT observe"). Each card has
"Activate" → `POST /outbound/activate/{founder_id}` → modal showing the
outreach draft {subject, body} with a copy button.
Founder detail (`GET /founders/{id}`) shows evidence list + full score history.

### 5. Thesis panel — `GET /thesis`, `PUT /thesis`
Simple form over the config: name, sectors (tags), stages, geographies, check
size, risk posture (select: back_potential_over_traction / balanced /
traction_first), axis weights (3 sliders, labeled "recommendation emphasis —
does not merge axes"). Save → PUT (send the full object back including id).
Banner: "Every score is computed through this lens."

### Inbound application form (modal from Pipeline): `POST /apply`
multipart form: company_name, founder_name, founder_email (optional), one_liner
(optional), deck (file: .md or .pdf). On success show evidence_created +
evidence_deduplicated, then offer "Run full pipeline".

Empty states everywhere ("No memo yet — run the pipeline"). Loading states for
pipeline run (it takes ~2 minutes; poll nothing, just await the POST and show
the staged timeline as it returns). Errors as toast.
