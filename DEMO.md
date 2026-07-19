# BrainVC — Demo Run-of-Show

**Setup (before judges arrive):**
1. `cd backend && uv run uvicorn app.api.main:app --port 8000`
2. `cd frontend && npm run dev` → http://localhost:8080
3. Confirm keys in `backend/.env`: OPENAI, TAVILY (ELEVENLABS optional → voice button).
4. Pipeline is pre-seeded (`uv run python seeds/seed_demo.py`) — the demo READS
   persisted results; the live run is the showpiece, not the safety net (risk R-2).

**The one-sentence pitch:** Every claim traces to evidence, trust rules are code
not vibes, and the Founder Score follows the person — not the pitch deck.

---

## Beat 1 — The ranked pipeline (30s)
Open Pipeline. Point at:
- Three axis meters per row — **never averaged** (footnote on screen).
- QuantumYieldCoin at the bottom: **rejected at gate** (the scam deck).
- PromptPantry ranked low: consumer + Berlin, **off-thesis** — same founder would
  score differently under a different thesis (open Thesis panel to show the lens).

## Beat 2 — Trust is the product (60s)
Open **NimbusOps → memo** (the planted-contradiction deck):
- ESCALATE banner: guardrail — contradicted revenue claims **structurally cannot**
  produce an INVEST decision.
- Click a **FLAGGED chip** on "$40K MRR" → drawer shows the exact deck slide
  asserting it AND the slide contradicting it ("currently pre-revenue").
- Market claims flagged by **real web evidence** (Tavily URLs in the drawer):
  the deck said $5.2B/30% CAGR; market reports disagree.
- "Declared gaps — not fabricated" panel: the memo marks what it does NOT know.
- (If ElevenLabs key set: hit **Voice briefing**.)

## Beat 3 — Cold start: score a founder with zero traction (45s)
Open **Founders** → scan a GitHub handle live (use a teammate's).
- 5 footprint dimensions, each with cited evidence.
- **"What we could NOT observe"** — the system states its own blind spots.
- Founder cards show score history sparklines (the credit score that never resets).
- Hit **Activate** → outreach draft citing their actual repos.

## Beat 4 — Convergence: the loop closes (45s)
The founder scanned in Beat 3 **applies inbound** (BrainVC's own deck, founder
Jithendra Puppala). Run the pipeline live (~2 min — start it, narrate over it):
- Trace shows: *"founder axis informed by persisted Founder Score"* — outbound
  memory feeding inbound scoring. Two tracks, one funnel, one person-level memory.
- Timeline shows staged timings: **application → decision in ~2 minutes**
  (vs. the brief's 24-hour bar).

## Beat 5 — Reality check: famous decks, real founders (45s)
Four REAL seed decks are in the pipeline (sources: REAL_DECKS.md) — Airbnb 2008,
Buffer 2011, Coinbase 2012, UberCab 2008, transcribed from the decks their
founders published:
- "We ran **Airbnb's actual seed deck** through the pipeline — here's the memo."
- Watch which 2008 claims the validator SUPPORTS from the historical record vs.
  leaves UNVERIFIABLE (Tavily finds the famous numbers).
- All four became $10B+ outcomes from decks full of unverifiable claims — the
  system escalates them, which IS the pre-seed problem stated by a machine.
- Thesis lens: they score off-thesis under the AI-enterprise preset; switch to
  the `classic_seed` preset (Thesis page) and re-run one to watch it re-rank.
- Founders pool now includes REAL scans: @rauchg (Vercel — sponsor!),
  @kiwicopple (Supabase — sponsor!), @mitchellh (HashiCorp) — live GitHub
  footprint scores next to yours.

## Closing line (10s)
"Every number you saw traces to a slide, a repo, or a URL. The system knows what
it knows, says what it doesn't, and refuses to invest when the evidence
contradicts itself. That's the VC brain."

---

## Judge Q&A ammo
- **Axes averaged?** Never — independent scores, trends, and stances; the
  ordering key is thesis-weighted and labeled ordering-only (brief FAQ 5).
- **Cold start?** 5-dimension public-footprint rubric + explicit known-unknowns,
  persisted as append-only Founder Score (brief FAQ 10 / Area of Research 3).
  Research framing: freeze assessments at time T, measure rank correlation
  against outcomes at T+18mo, per dimension.
- **Hallucinated citations?** Impossible by construction: models cite evidence
  by index; UUIDs are substituted in code; uncited claims are dropped.
- **Confidence bands?** Honest heuristics (evidence count, avg claim trust,
  single-source penalty) — the basis string is displayed, never disguised as
  statistical calibration.
- **What's synthetic?** Company decks + 3 pool founders (labeled SYNTHETIC in
  evidence). GitHub scans, Tavily verification, and all scoring are real.
- **Why does nothing say INVEST?** By design: every seeded deck is single-source
  self-reports, and the system refuses to deploy $100K on uncorroborated claims —
  it escalates with a precise list of what a human must verify. A deck alone can
  never trigger a check; independently supported evidence can.
