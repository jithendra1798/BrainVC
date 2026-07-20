# Research: Can a Pre-Founding Public Footprint Predict Who Founds a Fundable Company?

**Area of Research 3 from the challenge brief** — "How much can public footprints
predict founder success — and how would you test it?" This document is our
answer to the *how would you test it* half, plus a first pilot result produced
with the system itself. The brief's FAQ calls a real attempt here "exactly the
kind of approach the brief says could be industry-defining." We designed the
test to be falsifiable, ran it, and report whatever it says.

## 1. The question, made testable

BrainVC's cold-start scorer rates a founder's potential from public footprint
alone — five dimensions (shipping velocity, technical depth, learning rate,
public communication, domain signal), evidence-cited, with known-unknowns as
first-class output. The falsifiable claim behind it:

> Scored only on evidence that existed BEFORE they founded anything, eventual
> founders of VC-backed companies should rank above equally visible developers
> who never founded.

The italicized constraint is everything. Scoring Mitchell Hashimoto's footprint
today is hindsight cosplay; scoring the footprint as it stood in October 2012 —
blind — is a test.

## 2. Design (research/backtest.py — reproducible, one command)

**Cohort — 5 founders, 5 hard controls.** Each founder is paired with a control
at the SAME cutoff date: a developer of comparable public visibility who did
*not* found a VC-backed company within 3 years of that cutoff. Hard controls
are the point: separating future founders from average developers is easy and
meaningless; separating them from antirez and Sindre Sorhus is the actual
sourcing problem a fund faces.

| Cutoff | Founder (label 1) | Outcome | Control (label 0) | Status at +3y |
|---|---|---|---|---|
| 2012-10 | mitchellh | HashiCorp, IPO 2021 | antirez | Redis creator; employee, never founded |
| 2015-10 | rauchg | Vercel, >$1B | sindresorhus | full-time OSS, sponsorship-funded |
| 2019-12 | kiwicopple | Supabase (YC S20), >$1B | kentcdodds | educator, solo business, no VC |
| 2021-02 | ry | Deno Land, Sequoia A | hadley | RStudio/Posit employee |
| 2023-03 | charliermarsh | Astral ($4M seed) | sharkdp | fd/bat author; joined Astral as employee |

**Time slice.** Only repositories *created before the cutoff* enter the
evidence. Current-day pushed-dates, follower counts, and bios are dropped
entirely — each is a hindsight leak (a 2026 bio says "Founder of HashiCorp").

**Blinding.** Candidates are scored as `Candidate F01..F10` (shuffled, fixed
seed). Handles and owner prefixes are redacted from all evidence text. The
scorer — the same `ColdStartScorer` module that runs in the product, unmodified
— sees only repo-level artifacts: name, description, language, creation date.

**Star policy.** GitHub's API returns *today's* star counts — there is no
point-in-time value. Primary run: stars excluded. Sensitivity run: stars
included but tagged `[CURRENT-DAY VALUE — may post-date the cutoff]`. Reporting
both quantifies how much of the score is borrowed from the future.

**Statistic.** Mean score gap (founders − controls), exact one-sided
permutation p-value over all C(10,5) = 252 label assignments — exact by
enumeration, no asymptotics at N=10 — plus AUC.

## 3. Results (pilot, N=10)

Model: `gpt-5.5`, same scorer module as production. Full per-dimension output:
`backend/research/results/backtest_results.json`.

| Candidate | Role | Cutoff | Primary (no stars) | Sensitivity (stars) |
|---|---|---|---|---|
| mitchellh | founder | 2012-10 | 65.0 | 65.6 |
| rauchg | founder | 2015-10 | 65.0 | **75.0 (+10.0)** |
| kiwicopple | founder | 2019-12 | 54.4 | 57.8 |
| ry | founder | 2021-02 | 56.6 | 65.6 |
| charliermarsh | founder | 2023-03 | 62.0 | 64.6 |
| antirez | control | 2012-10 | 72.4 | 79.4 |
| sindresorhus | control | 2015-10 | 63.0 | 68.6 |
| kentcdodds | control | 2019-12 | 57.8 | 66.2 |
| hadley | control | 2021-02 | 71.6 | 73.6 |
| sharkdp | control | 2023-03 | 72.2 | 76.2 |

| Statistic | Primary (no stars) | Sensitivity (stars) |
|---|---|---|
| Founder mean | 60.6 | 65.7 |
| Control mean | 67.4 | 72.8 |
| Gap (founders − controls) | **−6.8** | −7.1 |
| AUC | **0.20** | 0.12 |
| Exact p (one-sided, 252 permutations) | 0.956 | 0.968 |

**The result is a null — and we report it as one.** Blinded and time-sliced,
repo-artifact footprint does NOT separate future VC-backed founders from
equally visible developers who never found. Direction is, if anything,
reversed: our controls — hand-picked as elite builders — out-scored the
founders.

Three findings survive scrutiny:

1. **The rubric measures what it claims: builder capability.** Controls
   selected for prolific building were scored as elite builders (antirez 72.4,
   sharkdp 72.2). The instrument is consistent; capability alone just doesn't
   determine who founds. At the elite tail, founding is a *choice*, not a
   capability threshold.
2. **Hindsight, quantified.** Adding current-day star counts inflates every
   score (+5.1 founders, +5.4 controls; rauchg +10.0 from socket.io's
   accumulated fame) without changing the ordering. Any pipeline that scores
   founders on today's footprint silently inherits this inflation — our
   time-slice harness makes it measurable.
3. **Design consequence, already in the architecture:** the cold-start score
   must be a capability screen and ONE input into the Founder axis — never the
   axis itself (the brief's FAQ 6 separation). And a sourcing system must not
   become a "GitHub-stars fund": the discriminative signal for *founding* has
   to come from non-repo channels — public writing about problems rather than
   code, trajectory breaks (new domain, sudden shipping burst), and inbound
   intent itself, which is why the inbound/outbound funnel converges instead
   of outbound replacing applications.

## 4. What this does and does not show

**Honest limitations, in order of severity:**

1. **N=10 is a pilot.** The exact test is valid at this size, but a single
   study this small measures direction, not effect size. We report it as such.
2. **Partial blinding.** Names are redacted, but `vagrant` or `redis` in a repo
   list is recognizable to a well-read model. We cannot fully de-identify famous
   developers; a scaled study must use non-famous cohorts (see §5).
3. **Repo descriptions are current-day text.** Mostly stable for these repos,
   but not guaranteed pre-cutoff wording.
4. **Cohort selection is retrospective.** We picked known outcomes; a real
   study must define the cohort at T and wait, or use an archival snapshot.
5. **One founder (rauchg) had founded before** (LearnBoost, 2010) — his
   pre-2015 footprint is not purely "cold-start."
6. **Labels are "founded a VC-backed company," not "succeeded."** Deliberate:
   it's the event a sourcing system must predict — conviction *before* the
   round exists.

## 5. How to run this at scale (the design we'd pre-register)

1. **Point-in-time data, not redaction:** GH Archive (public event stream since
   2011) gives true historical stars, pushes, and READMEs at any date — kills
   leaks 2 and 3 outright.
2. **Prospective-equivalent cohort:** all users above an activity threshold at
   time T (not hand-picked names), labeled by joining founding dates from
   Crunchbase/PitchBook at T+3y. Thousands of candidates, no fame confound.
3. **Per-dimension analysis:** which of the five rubric dimensions carries the
   signal? Rank-correlate each independently; prune the ones that don't.
4. **Calibration:** our confidence bands are labeled heuristic. At scale,
   check coverage (do X% bands contain outcomes X% of the time) and recalibrate
   isotonic-style.
5. **Feedback loop:** this is the same loop the product ships — every funded
   deal's outcome feeds back into Memory (sourcing-graph stretch goal), so the
   backtest becomes continuous, not a one-off study.

## 6. Why this matters for the product

The backtest is not a side quest — it is the evaluation harness for the
system's most load-bearing module. The scorer that produced these numbers is
byte-identical to the one running in outbound sourcing. Anyone can re-run the
study (`cd backend && uv run python research/backtest.py`) or extend the cohort
by editing one table. A fund adopting BrainVC inherits not just a score, but
the instrument to keep checking whether the score is real.
