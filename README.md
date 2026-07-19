# BrainVC — The VC Brain

AI-first operating system for venture capital: sources founders (inbound decks +
outbound GitHub scans), extracts and adversarially verifies every claim, scores
three independent axes under a configurable fund thesis, and produces an
evidence-backed investment memo with per-claim trust scores — application to
guardrailed $100K decision in ~2 minutes.

Built for the Hack-Nation 6th Global AI Hackathon · Challenge 02 (Maschmeyer Group).

**Docs:** [ARCHITECTURE.md](ARCHITECTURE.md) (contracts & module boundaries — read first) ·
[DECISIONS.md](DECISIONS.md) · [DEMO.md](DEMO.md) (run-of-show) ·
[REAL_DECKS.md](REAL_DECKS.md) (real-deck test provenance) ·
[PITCH_DECK.html](PITCH_DECK.html) (presentation — open in a browser)

## Setup from clone

Requirements: Python 3.12+ with [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
# 1. Keys (backend/.env is gitignored — never commit it)
cp backend/.env.example backend/.env
#    fill in: OPENAI_API_KEY (required), TAVILY_API_KEY (web verification),
#             ELEVENLABS_API_KEY (voice briefing) — features degrade gracefully
#             when a key is absent.

# 2. Backend (API on :8000)
cd backend && uv sync
uv run uvicorn app.api.main:app --port 8000 --reload

# 3. Frontend (UI on :8080) — use npm (bun lockfile is a Lovable export artifact)
cd frontend && npm install
npm run dev

# 4. Optional: seed the demo pipeline (backend API must be running)
cd backend
uv run python seeds/seed_demo.py   # synthetic funnel + founder pool
uv run python seeds/seed_real.py   # real decks (Airbnb '08, Buffer '11, ...) + real founder scans
```

App: http://localhost:8080 · API docs: http://localhost:8000/docs

## Collaborating

- **The contracts are the law**: modules depend only on `backend/app/contracts/`
  and `backend/app/memory/` repositories — never on a sibling module's internals.
  Swap any scorer/connector/validator behind its interface; see ARCHITECTURE §3.
- **All SQL lives in `memory/repositories.py`.** Scores and Founder Score entries
  are append-only — never UPDATE a score row.
- **Trust rules are code**: the extractor can't raise trust, only the validator
  can; contradicted revenue/traction claims can never yield INVEST.
- Frontend↔backend mapping lives in one place: `frontend/src/lib/api.ts`.
- The local SQLite DB (`backend/data/`) and uploads are gitignored — your
  pipeline runs stay local.

```bash
# Inbound application (deck + company name = minimum bar)
curl -X POST localhost:8000/api/apply \
  -F company_name=NimbusOps -F "founder_name=Ada Vance" \
  -F deck=@seeds/decks/nimbusops.md
```

## Test

```bash
cd backend && uv run pytest
```

## Keys (stage 2+)

Copy `backend/.env.example` → `backend/.env`. Stage 1 (sourcing/ingestion) needs
no keys; extraction, scoring, and validation need `OPENAI_API_KEY` + `TAVILY_API_KEY`.

## Pipeline status

| Stage | Status |
|---|---|
| Memory + Thesis + Trace foundation | ✅ built, tested |
| Sourcing: inbound deck (md + PDF) | ✅ built, tested |
| Ingestion: dedup + entity resolution | ✅ built, tested |
| Extraction: Evidence → Claims | ✅ live verified (25 claims, all traced) |
| Screening: gate + 3-axis scores | ✅ live verified (independent axes + honest bands) |
| Diligence: validator + trust scores | ✅ live verified (3 contradictions flagged); Tavily hook dormant until key |
| Decision: memo + recommendation | ✅ live verified (guardrailed escalate_to_human) |
| Full pipeline `/run` | ✅ 116s from application to decision, staged timings |
| Diligence: Tavily external verification | ✅ live verified (deck market claims contradicted by real web data) |
| Outbound: GitHub connector | ✅ live verified (real founder scanned) |
| Cold-start Founder Score (5-dim rubric + known unknowns) | ✅ live verified, append-only history |
| Activate: outreach draft citing real repos | ✅ live verified |
| Frontend (Lovable export + adapter layer) | ✅ all 5 screens verified rendering live data |

**One-command demo:** apply via `/api/apply`, then
`POST /api/opportunities/{id}/run` — extract → gate → 3-axis score →
validate → post-diligence re-score → memo. Ranked list: `GET /api/pipeline/ranked`.
