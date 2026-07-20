"""Time-machine backtest: does a PRE-FOUNDING public footprint predict who
goes on to found a VC-backed company? (Brief: Area of Research 3.)

Design
------
- Cohort: 5 eventual founders of VC-backed companies + 5 matched hard controls
  (equally prolific OSS developers at the same cutoff dates who did NOT found
  a VC-backed company within 3 years of the cutoff).
- Time slice: only repos CREATED before each candidate's cutoff enter the
  evidence. Current-day pushed dates, follower counts and bios are dropped
  (hindsight leaks). Star counts are excluded from the primary run and added
  only in a labeled sensitivity run.
- Blinding: candidates are scored as "Candidate F01..F10"; handles and owner
  prefixes are redacted from evidence. (Famous repo names remain partially
  recognizable — reported as a limitation.)
- Statistic: difference in mean cold-start score, founders vs controls, with
  an EXACT permutation p-value (all C(10,5)=252 label assignments) plus AUC.

Run:  cd backend && uv run python research/backtest.py
Writes research/results/backtest_results.json and prints a table.
"""

import hashlib
import itertools
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.contracts.entities import FounderRecord  # noqa: E402
from app.contracts.enums import SourceType  # noqa: E402
from app.contracts.evidence import Evidence  # noqa: E402
from app.llm.config import MODELS  # noqa: E402  (also loads backend/.env)
from app.scoring.cold_start.scorer import ColdStartScorer  # noqa: E402
from app.sourcing.connectors.github import _headers  # noqa: E402

API = "https://api.github.com"
MAX_REPOS = 10
RESULTS = Path(__file__).parent / "results"

# label 1 = founded a VC-backed company within 3 years AFTER cutoff.
# outcome notes are for the report only — the model never sees them.
COHORT = [
    dict(handle="mitchellh", cutoff="2012-10-01", label=1,
         note="HashiCorp (founded 2012-11; IPO 2021)"),
    dict(handle="rauchg", cutoff="2015-10-01", label=1,
         note="Vercel/ZEIT (founded 2015-11; >$1B). Prior founder (LearnBoost) — noted as contamination."),
    dict(handle="kiwicopple", cutoff="2019-12-01", label=1,
         note="Supabase (YC S20, founded 2020-01; >$1B)"),
    dict(handle="ry", cutoff="2021-02-01", label=1,
         note="Deno Land (founded 2021-03; Sequoia Series A 2022)"),
    dict(handle="charliermarsh", cutoff="2023-03-01", label=1,
         note="Astral (announced 2023-04, $4M seed; ruff pre-dates company)"),
    dict(handle="antirez", cutoff="2012-10-01", label=0,
         note="Redis creator; joined Redis Labs as employee, never founded"),
    dict(handle="sindresorhus", cutoff="2015-10-01", label=0,
         note="Full-time OSS, sponsorship-funded; never founded"),
    dict(handle="kentcdodds", cutoff="2019-12-01", label=0,
         note="Educator; solo businesses, not VC-backed"),
    dict(handle="hadley", cutoff="2021-02-01", label=0,
         note="RStudio/Posit employee; never founded"),
    dict(handle="sharkdp", cutoff="2023-03-01", label=0,
         note="fd/bat/hyperfine author; joined Astral 2023 as employee, not founder"),
]


def fetch_time_sliced(handle: str, cutoff: str, with_stars: bool) -> list[dict]:
    """Repos created strictly before cutoff, newest-first. No pushed dates,
    no follower counts, no bio — those are current-day values (hindsight)."""
    pre: list[dict] = []
    with httpx.Client(headers=_headers(), timeout=30) as client:
        # Walk oldest→newest and stop at the cutoff: complete for prolific
        # accounts (500+ repos) where the newest pages are all post-cutoff.
        for page in range(1, 12):
            r = client.get(f"{API}/users/{handle}/repos",
                           params={"per_page": 100, "page": page,
                                   "sort": "created", "direction": "asc"})
            r.raise_for_status()
            batch = r.json()
            hit_cutoff = False
            for repo in batch:
                if repo.get("created_at", "9999")[:10] >= cutoff:
                    hit_cutoff = True
                    break
                if not repo.get("fork"):
                    pre.append(repo)
            if hit_cutoff or len(batch) < 100:
                break
    pre.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return pre[:MAX_REPOS]


def redact(text: str, handle: str, blind_id: str) -> str:
    text = re.sub(re.escape(handle), blind_id, text or "", flags=re.IGNORECASE)
    return text


def build_evidence(handle: str, blind_id: str, cutoff: str,
                   repos: list[dict], with_stars: bool) -> list[Evidence]:
    evidence = []
    for repo in repos:
        name = repo["name"]  # short name only — owner prefix identifies
        desc = redact(repo.get("description") or "no description", handle, blind_id)
        content = (f"Repository '{redact(name, handle, blind_id)}': {desc}. "
                   f"Language: {repo.get('language') or 'unknown'}. "
                   f"Created {repo.get('created_at', '?')[:10]}.")
        if with_stars:
            content += (f" Stars: {repo.get('stargazers_count', 0)} "
                        f"[CURRENT-DAY VALUE — may post-date the cutoff].")
        evidence.append(Evidence(
            source_type=SourceType.GITHUB,
            source_ref=f"repo:{blind_id}/{len(evidence)}",
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            observed_at=datetime.fromisoformat(
                repo["created_at"].replace("Z", "+00:00")),
        ))
    return evidence


class _NullRepo:
    def save(self, entry):  # research runs must not touch the product DB
        pass


class _NullTrace:
    def log(self, *args, **kwargs):
        pass


def exact_permutation_p(scores: list[float], labels: list[int]) -> float:
    """One-sided exact test: P(mean-gap >= observed) over all label assignments."""
    n = len(scores)
    ones = sum(labels)
    observed = (sum(s for s, l in zip(scores, labels) if l) / ones
                - sum(s for s, l in zip(scores, labels) if not l) / (n - ones))
    count = 0
    total = 0
    for combo in itertools.combinations(range(n), ones):
        gap = (sum(scores[i] for i in combo) / ones
               - sum(scores[i] for i in range(n) if i not in combo) / (n - ones))
        if gap >= observed - 1e-9:
            count += 1
        total += 1
    return count / total


def auc(scores: list[float], labels: list[int]) -> float:
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0
               for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def run(with_stars: bool) -> list[dict]:
    scorer = ColdStartScorer(_NullRepo(), _NullTrace())
    blind = list(range(len(COHORT)))
    random.Random(42).shuffle(blind)  # fixed seed → reproducible blind IDs
    rows = []
    for idx, person in enumerate(COHORT):
        blind_id = f"Candidate F{blind[idx]+1:02d}"
        repos = fetch_time_sliced(person["handle"], person["cutoff"], with_stars)
        evidence = build_evidence(person["handle"], blind_id, person["cutoff"],
                                  repos, with_stars)
        founder = FounderRecord(canonical_name=blind_id)
        assessment = scorer.assess(founder, evidence)
        rows.append(dict(
            handle=person["handle"], blind_id=blind_id, cutoff=person["cutoff"],
            label=person["label"], note=person["note"],
            n_repos_pre_cutoff=len(repos),
            score=assessment.aggregate,
            band=[assessment.confidence.low, assessment.confidence.high],
            dimensions={k: v.score for k, v in assessment.dimension_scores.items()},
            known_unknowns=assessment.known_unknowns,
        ))
        print(f"  {person['handle']:>15} ({'founder' if person['label'] else 'control'})"
              f" cutoff={person['cutoff']} repos={len(repos)}"
              f" score={assessment.aggregate}", flush=True)
    return rows


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    report = {"model": MODELS["score"], "ran_at": datetime.now(timezone.utc).isoformat(),
              "design": "time-sliced pre-cutoff repos, name-blinded, hard controls"}
    for variant, with_stars in (("primary_no_stars", False),
                                ("sensitivity_with_stars", True)):
        print(f"\n=== {variant} ===", flush=True)
        rows = run(with_stars)
        scores = [r["score"] for r in rows]
        labels = [r["label"] for r in rows]
        f_mean = sum(s for s, l in zip(scores, labels) if l) / sum(labels)
        c_mean = sum(s for s, l in zip(scores, labels) if not l) / (
            len(labels) - sum(labels))
        stats = dict(founder_mean=round(f_mean, 1), control_mean=round(c_mean, 1),
                     gap=round(f_mean - c_mean, 1),
                     auc=round(auc(scores, labels), 3),
                     exact_p_one_sided=round(exact_permutation_p(scores, labels), 3))
        report[variant] = {"rows": rows, "stats": stats}
        print(f"  stats: {stats}", flush=True)
    out = RESULTS / "backtest_results.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nwrote {out}", flush=True)


if __name__ == "__main__":
    main()
