"""Confidence band v1: deterministic heuristic, honestly labeled.

Not statistical calibration — the basis string says exactly what widened the
band so the UI can show it. Driven by average per-claim trust, so the band
narrows only when the validator actually corroborates claims (and stays wide
when claims are contradicted). Swappable for k-sample agreement later without
touching any scorer.
"""

import math

from app.contracts.scores import ConfidenceBand


def compute_band(score: float, *, evidence_count: int, avg_trust: float,
                 distinct_source_types: int) -> ConfidenceBand:
    half_width = 4.0
    half_width += 18.0 * (1.0 - max(0.0, min(1.0, avg_trust)))
    half_width += 12.0 / max(1.0, math.sqrt(max(evidence_count, 1)))
    if distinct_source_types <= 1:
        half_width += 8.0

    parts = [f"{evidence_count} evidence items",
             f"avg claim trust {avg_trust:.2f}"]
    if distinct_source_types <= 1:
        parts.append("single-source (self-reported only)")

    return ConfidenceBand(
        low=max(0.0, round(score - half_width, 1)),
        high=min(100.0, round(score + half_width, 1)),
        basis="heuristic — " + ", ".join(parts),
    )
