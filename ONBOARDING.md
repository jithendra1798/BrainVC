# BrainVC — Team Onboarding

**Repo:** https://github.com/jithendra1798/BrainVC (public)
**What it is:** The VC Brain — Hack-Nation 6th Global AI Hackathon, Challenge 02
(Maschmeyer Group). An AI-first VC operating system: sources founders (inbound
decks + outbound GitHub scans), extracts and adversarially verifies every claim,
scores 3 independent axes under a configurable fund thesis, and emits an
evidence-backed memo with per-claim trust scores — application → guardrailed
$100K decision in ~2 minutes. **Submission deadline: Sunday 9:00 AM ET.**

## Get running (≈3 minutes)

```bash
git clone https://github.com/jithendra1798/BrainVC.git && cd BrainVC
cp backend/.env.example backend/.env   # add your own keys:
# OPENAI_API_KEY  (required — pipeline LLM calls)
# TAVILY_API_KEY  (optional — external web verification in the validator)
# ELEVENLABS_API_KEY (optional — voice briefing button on memos)

cd backend && uv sync
uv run uvicorn app.api.main:app --port 8000 --reload     # API :8000

cd ../frontend && npm install && npm run dev             # UI :8080  (use npm, not bun)

# optional demo data (API must be running):
cd ../backend
uv run python seeds/seed_demo.py    # synthetic funnel + founder pool
uv run python seeds/seed_real.py    # Airbnb '08 / Buffer '11 / Coinbase '12 / UberCab '08 + real founder scans
```

App: http://localhost:8080 · API docs: http://localhost:8000/docs · Tests: `cd backend && uv run pytest`

## How the system fits together

Pipeline stages (each an independent module): **Source → Screen (gate + 3 axes)
→ Diligence (validator + Tavily) → Decide (memo + recommendation)**, over an
append-only **Memory** (SQLite via repositories), under a configurable
**Thesis**. Cross-cutting: trace log (every step, every module) and confidence
bands (honest heuristics, basis displayed).

## House rules (please keep these true)

1. **Contracts are the law** — modules import only `backend/app/contracts/` and
   `backend/app/memory/` repositories, never a sibling module. (ARCHITECTURE.md §3)
2. **All SQL lives in `memory/repositories.py`.** Score tables are append-only —
   never UPDATE a score row; trends depend on history.
3. **Trust rules are code**: extraction cannot raise trust (claims are born
   skeptical); only the validator can. Contradicted revenue/traction claims can
   never produce INVEST — that guardrail is deterministic, don't soften it.
4. **Citations by index**: LLMs cite evidence by list index; UUIDs are
   substituted in code. Never let a model emit a raw ID.
5. Frontend↔backend shape mapping lives ONLY in `frontend/src/lib/api.ts`
   (scores are 0–100 in the API, 0–1 in the UI).
6. `backend/.env` and `backend/data/` are gitignored — keys and local pipeline
   state never get committed.

## Where things are

| What | Where |
|---|---|
| Data contracts (read first) | `backend/app/contracts/` |
| Pipeline orchestrator | `backend/app/pipeline/orchestrator.py` |
| Gate / axis scorers / cold-start | `backend/app/screening/`, `backend/app/scoring/` |
| Validator (+ Tavily hook) | `backend/app/validation/` |
| Memo + voice briefing | `backend/app/memo/` |
| Model tiers per role (env-overridable) | `backend/app/llm/config.py` |
| UI routes (TanStack Start) | `frontend/src/routes/` |
| Demo run-of-show + judge Q&A | `DEMO.md` |
| Presentation (8 slides, browser) | `PITCH_DECK.html` (arrows to navigate, `?slide=N`) |
| Real-deck test provenance | `REAL_DECKS.md` |

## Current state (all live-verified)

Full pipeline works end-to-end (~2 min/opportunity, staged timings in `/run`
response). Seeded funnel: every stage represented, scam deck rejected at gate,
off-thesis deck gets explained PASS. Real decks (Airbnb/Buffer/Coinbase/UberCab)
run and ESCALATE honestly. Real founder cold-start scans: Hashimoto 85.6,
Rauch 81.4, Copplestone 75.8. Voice briefings working. 6/6 tests pass.

**Open/nice-to-have:** NL multi-attribute query over memory (brief MVP item 3,
thin version planned), Tavily result domain filtering, k-sample confidence
bands, sourcing-graph stretch goal. Coordinate in the team chat before touching
a module someone else is in — the contracts make parallel work safe.
