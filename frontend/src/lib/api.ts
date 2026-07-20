// BrainVC API client + adapter layer.
// The backend contract (FastAPI, http://localhost:8000/api) is the source of
// truth; this file adapts its responses into the shapes the UI components
// consume. All mapping lives HERE and nowhere else:
//   - scores/bands normalized 0-100 -> 0-1 (UI renders .toFixed(2) + 0-1 bars)
//   - trend improving/declining/stable -> up/down/flat
//   - claims joined with their evidence excerpts (backend keeps them separate)
export const API_BASE =
  (typeof window !== "undefined" &&
    (window as unknown as { __BRAINVC_API__?: string }).__BRAINVC_API__) ||
  (import.meta.env?.VITE_API_BASE as string | undefined) ||
  "http://localhost:8000/api";

export type TrustLevel = "high" | "medium" | "low" | "flagged";

export type AxisKey = "founder" | "market" | "idea_vs_market";

export interface Axis {
  score: number; // 0-1
  band: [number, number]; // 0-1
  trend?: "up" | "down" | "flat" | string;
  stance?: string | null;
  basis?: string | null;
  rationale?: string | null;
}

export interface OpportunityAxes {
  founder: Axis;
  market: Axis;
  idea_vs_market: Axis;
}

export type Recommendation = "invest_100k" | "escalate_to_human" | "pass" | string;

export interface PipelineOpportunity {
  opportunity_id: string;
  company_name: string;
  track: "inbound" | "outbound" | string;
  status: string;
  axes: OpportunityAxes;
  ordering_key: number;
  recommendation: Recommendation;
}

export interface PipelineResponse {
  thesis: { name: string };
  opportunities: PipelineOpportunity[];
}

export interface Evidence {
  relation: "asserts" | "supports" | "contradicts" | string;
  excerpt: string;
  source_ref?: string | null;
  source_type?: string | null;
  retrieved_at?: string | null;
}

export interface Claim {
  claim_id: string;
  category: string;
  text: string;
  status: string;
  trust: {
    level: TrustLevel;
    value: number;
    rationale?: string | null;
    verification_method?: string | null;
  };
  evidence: Evidence[];
}

export interface TraceEntry {
  module: string;
  step: string;
  summary: string;
  model?: string | null;
  timestamp: string;
}

export interface Opportunity {
  opportunity_id: string;
  company_name: string;
  track: string;
  status: string;
  one_liner?: string | null;
  founder_name?: string | null;
  recommendation?: Recommendation;
}

export interface MemoSection {
  kind: string;
  markdown: string;
}

export interface Memo {
  recommendation: Recommendation;
  recommendation_rationale: string;
  sections: MemoSection[];
  gaps: string[];
  claim_ids: string[];
}

export interface MemoResponse {
  memo: Memo;
  claims: Record<string, Claim>;
}

export interface Founder {
  founder_id: string;
  name: string;
  github_handle?: string | null;
  evidence_count: number;
  founder_score: { score: number; band: [number, number] };
  score_history: { timestamp: string; score: number }[];
}

export interface ColdStartDimension {
  name: string;
  score: number; // 0-1
  rationale: string;
}

export interface ColdStart {
  dimensions: ColdStartDimension[];
  known_unknowns: string[];
}

export interface ScanResponse {
  founder_id?: string;
  cold_start: ColdStart;
}

export interface Thesis {
  id?: string;
  name: string;
  sectors: string[];
  stages: string[];
  geographies: string[];
  check_size: number | string;
  risk_posture: "back_potential_over_traction" | "balanced" | "traction_first" | string;
  axis_weights: { founder: number; market: number; idea_vs_market: number };
  [k: string]: unknown;
}

// ---------- raw backend shapes (contracts) ----------

interface RawConfidence {
  low: number;
  high: number;
  basis: string;
}

interface RawAxisScore {
  score: number; // 0-100
  confidence: RawConfidence;
  trend: string; // improving | declining | stable | insufficient_history
  market_stance?: string | null;
  rationale: string;
}

interface RawEvidence {
  id: string;
  source_type: string;
  source_ref: string;
  content: string;
  retrieved_at: string;
}

interface RawClaim {
  id: string;
  category: string;
  text: string;
  status: string;
  trust: {
    value: number;
    level: TrustLevel;
    rationale: string;
    verification_method: string;
  };
  evidence_links: { evidence_id: string; relation: string }[];
}

interface RawOpportunityDetail {
  opportunity: { id: string; track: string; status: string };
  company: { name: string; one_liner?: string | null } | null;
  evidence: RawEvidence[];
}

// ---------- adapters ----------

const TREND: Record<string, string | undefined> = {
  improving: "up",
  declining: "down",
  stable: "flat",
  insufficient_history: undefined,
};

const n01 = (v: number) => Math.round((v / 100) * 100) / 100;

const UNSCORED_AXIS: Axis = { score: 0, band: [0, 1], basis: "not scored yet" };

function mapAxis(raw?: RawAxisScore | { score: number; band: [number, number]; trend?: string; stance?: string | null }): Axis {
  if (!raw) return UNSCORED_AXIS;
  if ("confidence" in raw) {
    return {
      score: n01(raw.score),
      band: [n01(raw.confidence.low), n01(raw.confidence.high)],
      trend: TREND[raw.trend],
      stance: raw.market_stance ?? null,
      basis: raw.confidence.basis,
      rationale: raw.rationale,
    };
  }
  // pipeline/ranked compact shape: {score, band, trend, stance}
  return {
    score: n01(raw.score),
    band: [n01(raw.band[0]), n01(raw.band[1])],
    trend: TREND[raw.trend ?? ""],
    stance: raw.stance ?? null,
  };
}

function joinEvidence(claim: RawClaim, evidenceById: Map<string, RawEvidence>): Claim {
  return {
    claim_id: claim.id,
    category: claim.category,
    text: claim.text,
    status: claim.status,
    trust: claim.trust,
    evidence: claim.evidence_links
      .map((link): Evidence | null => {
        const ev = evidenceById.get(link.evidence_id);
        if (!ev) return null;
        return {
          relation: link.relation,
          excerpt: ev.content,
          source_ref: ev.source_ref,
          source_type: ev.source_type,
          retrieved_at: ev.retrieved_at,
        };
      })
      .filter((e): e is Evidence => e !== null),
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const body = await res.text();
      if (body) msg = `${msg} — ${body.slice(0, 300)}`;
    } catch {}
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") ?? "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

async function opportunityEvidence(id: string): Promise<Map<string, RawEvidence>> {
  const detail = await request<RawOpportunityDetail>(`/opportunities/${id}`);
  return new Map(detail.evidence.map((e) => [e.id, e]));
}

export const api = {
  pipeline: async (): Promise<PipelineResponse> => {
    const raw = await request<{
      thesis: string;
      opportunities: {
        opportunity_id: string;
        company_name: string;
        track: string;
        status: string;
        axes: Record<string, { score: number; band: [number, number]; trend: string; stance?: string | null }>;
        ordering_key: number | null;
        recommendation: string | null;
      }[];
    }>("/pipeline/ranked");
    return {
      thesis: { name: raw.thesis },
      opportunities: raw.opportunities.map((o) => ({
        opportunity_id: o.opportunity_id,
        company_name: o.company_name,
        track: o.track,
        status: o.status,
        axes: {
          founder: mapAxis(o.axes.founder),
          market: mapAxis(o.axes.market),
          idea_vs_market: mapAxis(o.axes.idea_vs_market),
        },
        ordering_key: o.ordering_key ?? 0,
        recommendation:
          o.recommendation ??
          (o.status === "rejected_at_gate" ? "rejected" : "pending"),
      })),
    };
  },

  opportunity: async (id: string): Promise<Opportunity> => {
    const raw = await request<RawOpportunityDetail>(`/opportunities/${id}`);
    return {
      opportunity_id: raw.opportunity.id,
      company_name: raw.company?.name ?? "?",
      track: raw.opportunity.track,
      status: raw.opportunity.status,
      one_liner: raw.company?.one_liner ?? null,
    };
  },

  scores: async (id: string): Promise<{ axes: OpportunityAxes }> => {
    const raw = await request<Record<string, RawAxisScore>>(`/opportunities/${id}/scores`);
    return {
      axes: {
        founder: mapAxis(raw.founder),
        market: mapAxis(raw.market),
        idea_vs_market: mapAxis(raw.idea_vs_market),
      },
    };
  },

  claims: async (id: string): Promise<{ claims: Claim[] }> => {
    const [rawClaims, evidenceById] = await Promise.all([
      request<RawClaim[]>(`/opportunities/${id}/claims`),
      opportunityEvidence(id),
    ]);
    return { claims: rawClaims.map((c) => joinEvidence(c, evidenceById)) };
  },

  trace: async (id: string): Promise<{ trace: TraceEntry[] }> => {
    const raw = await request<
      { module: string; step: string; summary: string; model?: string | null; created_at: string }[]
    >(`/opportunities/${id}/trace`);
    return {
      trace: raw.map((e) => ({
        module: e.module,
        step: e.step,
        summary: e.summary,
        model: e.model,
        timestamp: e.created_at,
      })),
    };
  },

  memo: async (id: string): Promise<MemoResponse> => {
    const [raw, evidenceById] = await Promise.all([
      request<{ memo: Memo; claims: Record<string, RawClaim> }>(`/opportunities/${id}/memo`),
      opportunityEvidence(id),
    ]);
    const claims: Record<string, Claim> = {};
    for (const [cid, claim] of Object.entries(raw.claims)) {
      claims[cid] = joinEvidence(claim, evidenceById);
    }
    return { memo: raw.memo, claims };
  },

  runPipeline: async (id: string): Promise<{ timeline: TraceEntry[] }> => {
    const raw = await request<{
      timeline: { stage: string; elapsed_s: number; summary: string }[];
    }>(`/opportunities/${id}/run`, { method: "POST" });
    return {
      timeline: (raw.timeline ?? []).map((t) => ({
        module: t.stage,
        step: `t+${t.elapsed_s}s`,
        summary: t.summary,
        timestamp: new Date().toISOString(),
      })),
    };
  },

  founders: async (): Promise<{ founders: Founder[] }> => {
    const raw = await request<
      {
        id: string;
        name: string;
        handles: Record<string, string>;
        evidence_count: number;
        founder_score: number | null;
        score_history: { score: number; low: number; high: number; at: string }[];
      }[]
    >("/founders");
    return {
      founders: raw
        .filter((f) => f.founder_score !== null && f.score_history.length > 0)
        .map((f) => {
          const last = f.score_history[f.score_history.length - 1];
          return {
            founder_id: f.id,
            name: f.name,
            github_handle: f.handles?.github ?? null,
            evidence_count: f.evidence_count,
            founder_score: { score: n01(last.score), band: [n01(last.low), n01(last.high)] as [number, number] },
            score_history: f.score_history.map((h) => ({ timestamp: h.at, score: n01(h.score) })),
          };
        }),
    };
  },

  founder: async (id: string): Promise<Founder & { evidence: Evidence[] }> => {
    const raw = await request<{
      founder: { id: string; canonical_name: string; handles: Record<string, string> };
      evidence: RawEvidence[];
      score_history: { score: number; confidence: RawConfidence; created_at: string }[];
    }>(`/founders/${id}`);
    const last = raw.score_history[raw.score_history.length - 1];
    return {
      founder_id: raw.founder.id,
      name: raw.founder.canonical_name,
      github_handle: raw.founder.handles?.github ?? null,
      evidence_count: raw.evidence.length,
      founder_score: last
        ? { score: n01(last.score), band: [n01(last.confidence.low), n01(last.confidence.high)] }
        : { score: 0, band: [0, 1] },
      score_history: raw.score_history.map((h) => ({
        timestamp: h.created_at,
        score: n01(h.score),
      })),
      evidence: raw.evidence.map((e) => ({
        relation: "observed",
        excerpt: e.content,
        source_ref: e.source_ref,
        source_type: e.source_type,
        retrieved_at: e.retrieved_at,
      })),
    };
  },

  scanFounder: async (github_handle: string): Promise<ScanResponse> => {
    const raw = await request<{
      founder_id: string;
      cold_start: {
        dimension_scores: Record<string, { score: number; rationale: string }>;
        known_unknowns: string[];
      };
    }>("/outbound/scan", {
      method: "POST",
      body: JSON.stringify({ github_handle }),
    });
    return {
      founder_id: raw.founder_id,
      cold_start: {
        dimensions: Object.entries(raw.cold_start.dimension_scores).map(([name, d]) => ({
          name: name.replace(/_/g, " "),
          score: n01(d.score),
          rationale: d.rationale,
        })),
        known_unknowns: raw.cold_start.known_unknowns,
      },
    };
  },

  activateFounder: async (id: string) => {
    const raw = await request<{ draft: { subject: string; body: string } }>(
      `/outbound/activate/${id}`,
      { method: "POST" },
    );
    return { outreach: raw.draft };
  },

  thesis: async (): Promise<Thesis> => {
    const raw = await request<Record<string, unknown>>("/thesis");
    const weights = (raw.axis_weights as Thesis["axis_weights"]) ?? {
      founder: 1,
      market: 1,
      idea_vs_market: 1,
    };
    const sum = weights.founder + weights.market + weights.idea_vs_market || 1;
    return {
      id: raw.id as string,
      name: raw.name as string,
      sectors: (raw.sectors as string[]) ?? [],
      stages: (raw.stages as string[]) ?? [],
      geographies: (raw.geographies as string[]) ?? [],
      check_size: (raw.check_size_usd as number) ?? 100000,
      risk_posture: raw.risk_posture as Thesis["risk_posture"],
      axis_weights: {
        founder: Math.round((weights.founder / sum) * 100) / 100,
        market: Math.round((weights.market / sum) * 100) / 100,
        idea_vs_market: Math.round((weights.idea_vs_market / sum) * 100) / 100,
      },
    };
  },

  saveThesis: async (t: Thesis): Promise<Thesis> => {
    const body = {
      ...(t.id ? { id: t.id } : {}),
      name: t.name,
      sectors: t.sectors,
      stages: t.stages,
      geographies: t.geographies,
      check_size_usd: Math.round(Number(t.check_size)) || 100000,
      ownership_target_pct: null,
      risk_posture: t.risk_posture,
      axis_weights: t.axis_weights,
    };
    await request("/thesis", { method: "PUT", body: JSON.stringify(body) });
    return api.thesis();
  },

  apply: (form: FormData) =>
    request<{ opportunity_id: string; evidence_created: number; evidence_deduplicated: number }>(
      "/apply",
      { method: "POST", body: form },
    ),
};
