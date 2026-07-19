# BrainVC — Open Questions & Assumptions

Decisions I did NOT silently make. The forks (Q-1 … Q-8) need your call before
build; the assumptions (A-1 …) need only a veto if wrong.

---

## Forks needing your input

**Q-1 · Team composition (you asked me to confirm this).**
I assumed 2–3 people: one strong ML/backend (Python), ideally one full-stack.
- If we have a full-stack member → plan stands (FastAPI + Lovable/React).
- If we're 2 people, both backend → I'd cut the Lovable/React frontend to a
  Streamlit or minimal server-rendered UI and reinvest the time in the cold-start
  scorer. UX is 15%; the data layer is 30%.
**Who exactly is on the team, and what are they fastest in?**

**Q-2 · Python backend vs all-TypeScript.**
D-1 recommends FastAPI on the ML-strength assumption. If the real team is
TS-native, a single Next.js app (API routes + Zod contracts) is the better call
despite weaker data tooling. This decision is cheap now and expensive at hour 12.

**Q-3 · Backend hosting. — RESOLVED:** single machine, everything local.
Supabase free tier remains the DB; local Postgres (Docker) as WiFi fallback.

**Q-4 · How live is the demo?**
Option A (recommended): pre-run pipeline on all seed founders; demo walks
persisted results + one live inbound application as the showpiece.
Option B: everything live. Higher wow, much higher blast radius (R-2).

**Q-5 · OpenAI model tiers.**
I don't know what the hackathon credits actually unlock (models, rate limits).
Plan assumes: a cheap fast model for the viability gate + a stronger reasoning
model for scoring/validation/memo. **Needs verification at kickoff before we
budget k-sample confidence runs (k=3 per axis multiplies cost).**

**Q-6 · Tavily for external verification. — RESOLVED:** credits confirmed.
Validator does real external lookups via Tavily; promoted from stretch into P0/P1
validator. ElevenLabs credits also confirmed → optional UX flourish: voice
briefing of the memo. Emdash available → dev-time tool (parallel AI coding
agents), not part of the product.

**Q-7 · Real-founder data in the demo.**
Outbound demo is strongest on 2–3 real public figures (public GitHub/arXiv
footprints). Scoring real, named people on stage has optics risk (a low founder
score on a real person, on a projector). Alternatives: use consenting teammates
as the "real" founders, or fully synthetic. **Your comfort level?**

**Q-8 · Multi-attribute NL query scope.**
The brief lists it as MVP item 3 ("technical founder, Berlin, AI infra, …" in one
pass), but your build sequence omitted it. I slotted a thin version at P1.5
(one LLM call → structured filter + vector search). **Confirm it stays P1.5, or
promote/cut.**

**Q-9 · Cold-start scorer v1 method.**
Recommended: LLM rubric over extracted footprint features, with cited evidence
and explicit `known_unknowns` (buildable in 24h, transparent). Alternative: a
trained feature model — more "research-grade" for Area-of-Research 3, but needs
labeled outcome data we don't have and can't honestly fake overnight. I'd write
the research framing in the README instead (how we WOULD test footprint→success
prediction), which the brief's FAQ 11 explicitly rewards. **OK?**

---

## Assumptions (veto if wrong)

- **A-1** Submission = repo + demo video + live pitch; no requirement that the
  system be publicly hosted after the event.
- **A-2** Synthetic LinkedIn-shaped data (clearly labeled) is acceptable to
  judges; live LinkedIn scraping is not worth the ToS + breakage risk (D-7).
- **A-3** Judges will accept heuristic confidence bands **because** they're
  labeled honestly (`basis` field, "heuristic" UI label) — per the brief's own
  emphasis on transparency over false precision.
- **A-4** The three axes are never merged into one number anywhere in UI or API
  (brief FAQ 5 is explicit); thesis `axis_weights` affect emphasis in the
  recommendation logic only, and we display all three axes separately.
- **A-5** GitHub API unauthenticated rate limits may be too low for live demo
  use; assuming we can use a personal access token from a team member's account.
- **A-6** "$100K check deployment" is a recommendation output
  (`INVEST_100K`), not an actual payment integration.
- **A-7** English-only; no auth on the demo app; single shared thesis at a time
  (no multi-user concurrency).
- **A-8** Seed scale of 15–25 founders is enough to make the ranked list feel
  like a living pipeline; hundreds would add ingestion time, not judge value.
- **A-9** Trend indicators on demo day rely on back-dated seed history
  (ARCHITECTURE §4); real multi-day trend accumulation is impossible in 24h and
  we say so rather than fake it.

---

*Waiting on your answers to Q-1 … Q-9 (Q-1/Q-2 are the blocking ones) before any
implementation begins.*
