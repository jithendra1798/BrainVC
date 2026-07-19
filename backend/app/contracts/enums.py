from enum import StrEnum


class Stage(StrEnum):
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"


class RiskPosture(StrEnum):
    BACK_POTENTIAL_OVER_TRACTION = "back_potential_over_traction"
    BALANCED = "balanced"
    TRACTION_FIRST = "traction_first"


class Track(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class PipelineStatus(StrEnum):
    SOURCED = "sourced"
    SCREENED = "screened"
    IN_DILIGENCE = "in_diligence"
    DECIDED = "decided"
    REJECTED_AT_GATE = "rejected_at_gate"


class SourceType(StrEnum):
    DECK_SLIDE = "deck_slide"
    GITHUB = "github"
    ARXIV = "arxiv"
    HACKATHON = "hackathon"
    SOCIAL = "social"
    WEB = "web"
    APPLICATION_FORM = "application_form"
    SYNTHETIC = "synthetic"


class ClaimCategory(StrEnum):
    TRACTION = "traction"
    REVENUE = "revenue"
    TEAM = "team"
    MARKET = "market"
    PRODUCT = "product"
    OTHER = "other"


class ClaimStatus(StrEnum):
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNVERIFIABLE = "unverifiable"


class TrustLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FLAGGED = "flagged"


class Relation(StrEnum):
    ASSERTS = "asserts"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class Axis(StrEnum):
    FOUNDER = "founder"
    MARKET = "market"
    IDEA_VS_MARKET = "idea_vs_market"


class Trend(StrEnum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    INSUFFICIENT_HISTORY = "insufficient_history"


class Stance(StrEnum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEAR = "bear"


class Recommendation(StrEnum):
    INVEST_100K = "invest_100k"
    PASS = "pass"
    ESCALATE_TO_HUMAN = "escalate_to_human"


class SectionKind(StrEnum):
    SNAPSHOT = "snapshot"
    HYPOTHESES = "hypotheses"
    SWOT = "swot"
    PROBLEM_PRODUCT = "problem_product"
    TRACTION_KPIS = "traction_kpis"
    BEAR_CASE = "bear_case"
