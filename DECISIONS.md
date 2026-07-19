# BrainVC — Key Decisions

Each decision: realistic options, tradeoffs, recommendation. Biased toward what
2–3 people can ship in 24 hours and improve incrementally. Big forks that need
your sign-off are cross-referenced to OPEN_QUESTIONS.md.

---

## D-1 · Backend language & framework

| Option | For | Against |
|---|---|---|
| **Python + FastAPI** ✅ | Matches the ML-strong member; best LLM/PDF/data ecosystem (pydantic, pypdf, httpx); Pydantic models ARE the data contracts; auto-OpenAPI gives the frontend its types for free | Second deploy target besides Vercel (see D-6) |
| Next.js API routes (all-TS) | One repo, one Vercel deploy, one language | Fights the team's ML strength; weaker PDF/data tooling; contracts in Zod duplicate effort for the ML member |
| Supabase Edge Functions | Zero extra infra | Deno runtime restrictions, poor fit for a multi-step LLM pipeline, painful local dev under time pressure |

**Recommendation:** FastAPI. The pipeline is the product; put it in the language the
strongest builder is fastest in. → Fork Q-2 (if the team turns out to be all-TS, flip this).

## D-2 · Pipeline orchestration

| Option | For | Against |
|---|---|---|
| **Plain sequential async functions + module registry** ✅ | Zero framework risk; trivially debuggable at 3am; trace logging is just function calls; modularity comes from contracts, not a framework | No built-in retries/parallelism (we add a 10-line retry helper) |
| LangGraph / CrewAI / agent framework | Built-in state graphs, fancy demo diagram | Learning curve + version churn burns hours; failure modes are opaque; our DAG is a straight line — a framework adds nothing |
| Task queue (Celery/Redis) | Real async at scale | Absurd overkill for a 24h demo |

**Recommendation:** plain sequential. The brief's "agentic" feel comes from the
validator's adversarial role and the trace log — not from a framework.

## D-3 · Data store

| Option | For | Against |
|---|---|---|
| **Supabase (Postgres + pgvector)** ✅ | Sponsor credits; persistence + vector search + auth + hosted dashboard in one; append-only history tables are natural; survives laptop crashes before the demo | Slightly slower iteration than SQLite; needs migrations |
| SQLite local | Fastest start | No pgvector parity, no shared DB between teammates, dies with the laptop |
| In-memory + JSON dumps | Zero setup | "Memory layer, nothing discarded" is the brief's pillar — mocking it torpedoes the 30% data-architecture criterion |

**Recommendation (UPDATED after "single machine" call):** SQLite via SQLAlchemy.
Zero network dependency at demo time, zero credentials. Postgres/Supabase remains
a one-line connection-string swap because all SQL lives behind repositories. At
demo scale (~25 founders) vector search = cosine in Python over JSON-stored
embeddings; pgvector is unnecessary.

## D-4 · LLM usage pattern

| Option | For | Against |
|---|---|---|
| **One provider (OpenAI credits), role-specialized calls** ✅ | Each module gets its own prompt + strict JSON-schema structured output; validator runs a different prompt/temperature (ideally a different model tier) than the extractor to decorrelate errors; cheap gate model for screening, stronger model for scoring/memo | More prompts to maintain (bounded: ~6) |
| One mega-prompt does everything | Fewest calls | Un-traceable, un-swappable, monolith — violates the core principle |
| Multi-provider ensemble | True decorrelation for validator | Second API key/billing risk mid-hackathon; marginal demo value |

**Recommendation:** role-specialized calls on OpenAI. Exact model tiers: → Q-5
(I don't know current credit limits/model availability; verify at kickoff).
Every LLM call uses structured outputs with strict schemas — free insurance
against JSON drift.

## D-5 · State & memory persistence

Everything that any module produces is persisted immediately via repositories —
no pipeline state lives only in RAM. Scores and FounderScore entries are
append-only (never UPDATE), which is what makes trends and "never resets" true
rather than claimed. Re-running a pipeline creates new rows, keeping history.
**Alternative rejected:** in-process state with periodic snapshots — cheaper writes,
but one crash before the demo loses the story we're selling.

## D-6 · Deployment — RESOLVED: single machine

Everything runs on one laptop: FastAPI + frontend served locally. Supabase stays
as the hosted free-tier DB (it's just Postgres over the wire; the app still runs
from one machine). Fallback if venue WiFi is bad: local Postgres via Docker with
the same migrations. No cloud deploy, no cold-start risk.

## D-7 · Data acquisition (no dataset provided)

- **Real, safe, free:** GitHub REST API (public repos/commits — verify unauthenticated rate limits, else use a personal token), arXiv API. These make outbound sourcing *real*, which the brief rewards.
- **Synthetic:** 15–25 founder profiles with LinkedIn-shaped bios, decks (3–5 real-ish PDFs + rest as markdown), **seeded contradictions** (e.g. deck claims "$40K MRR", synthetic social post implies pre-revenue) so the validator has something visible to catch on stage.
- **Explicitly avoided:** live LinkedIn scraping (ToS violation + blocked mid-demo = double risk). LinkedIn-shaped data is synthetic and labeled as such in the UI (`SYNTHETIC` source type) — honesty here reads as rigor, not weakness.
- Back-dated evidence + founder-score history is seeded so trend indicators render (→ ARCHITECTURE §4).

## D-8 · Frontend approach

| Option | For | Against |
|---|---|---|
| **Lovable to generate the 4 screens against our OpenAPI contract, then hand-refine** ✅ | Sponsor tool; gets 80% of "Notion-approachability" for ~2 hours of effort; UX is only 15% of grade | Generated code can be messy — freeze it once acceptable, resist rewrites |
| Hand-built Next.js + shadcn | Full control, clean code | Burns the full-stack member's night on the smallest grading slice |
| Streamlit | ML member can build it alone | Looks like a data tool, not "investor-grade UX"; fallback only if we're 2 people both backend (→ Q-1) |

**Recommendation:** Lovable early (hour ~4, as soon as API contract is frozen), refine late.

---

## Build Sequence (tied to grading weights)

**P0 — thin end-to-end slice on ONE founder** *(hours 0–10; if this runs, we have a submission)*
1. Contracts + Supabase schema + repositories (the spine everything depends on)
2. Thesis preset loaded from JSON (config object, no UI yet)
3. InboundDeckConnector: parse ONE deck → Evidence
4. Extraction → Claims (structured output)
5. Three axis scorers (LLM-rubric v1) + viability gate
6. Validator pass over claims → trust scores + one seeded contradiction caught
7. Memo composer → required sections + gaps + recommendation
8. Minimal ranked list + memo view (Lovable), trace click-through on one claim

**P1 — the differentiators** *(hours 10–18)*
9. GitHub + arXiv connectors → real outbound signals on 2–3 real public founders
10. Cold-start scorer with dimension rubric + known_unknowns
11. ConfidenceWrapper: k-sample agreement bands on all axis scores
12. Founder Score history + trend rendering; thesis switch re-ranks the list live
13. Seed 15–25 founders so the ranked list looks like a pipeline, not a demo of one

**P1.5 — brief-mandated, cheap** *(hours 18–20)*
14. Multi-attribute NL query over memory (one LLM call → structured filter + vector search) — it's MVP item 3 in the brief; note it was absent from your P0/P1 (→ Q-8)
15. Outbound "Activate": generated outreach draft shown in UI (closes the brief's outbound loop)

**Stretch** *(only if P1 is demo-solid)*
- Sourcing-graph intelligence (channel → quality tracking)
- Real external verification via Tavily (→ Q-6)
- Better calibration (self-consistency variance across more samples)

**Out of scope (explicit):** portfolio monitoring, follow-on/exit modeling, fund ops,
auth/multi-tenancy, payments/check-writing rails, mobile, heavy design systems,
real LinkedIn/Twitter scraping, model fine-tuning.

---

## Risk Register

| # | Risk | Likelihood | Mitigation (architectural) |
|---|---|---|---|
| R-1 | **PDF deck parsing eats the night** (layout chaos, images-as-text) | High | Deck connector is just another `SourcingConnector`; accept markdown "decks" as first-class; pre-test 3 seed PDFs in hour 1; if PDFs misbehave, demo runs on markdown + 1 known-good PDF |
| R-2 | **Live API failure during demo** (OpenAI outage, rate limit, WiFi) | Medium | Everything persists (D-5): pre-run the full pipeline on all seed founders the night before; demo reads from Memory; live run is a bonus, not the spine |
| R-3 | **LLM output drift breaks the pipeline** mid-chain | Medium | Strict structured outputs everywhere; contracts validated at module boundaries so failures localize to one module; retry helper with schema re-prompt |
| R-4 | **Entity resolution rabbit hole** (fuzzy person matching is a PhD) | High | v1 = exact handle/email match + name+company similarity only; anything fuzzier goes to a "suggested merge" queue we never build UI for; capped at 2 hours |
| R-5 | **Confidence bands get challenged by judges** as fake statistics | Medium | Bands carry an explicit `basis` string; UI labels them "heuristic confidence"; the honesty IS the answer to the brief's "transparent about uncertainty" |
| R-6 | **Frontend integration crunch** in the last hours | Medium | API contract frozen at hour ~4; Lovable builds against OpenAPI from then on; ranked list + memo view prioritized, thesis panel can degrade to a preset dropdown |
