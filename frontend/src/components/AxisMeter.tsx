import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import type { Axis, AxisKey } from "@/lib/api";
import { cn } from "@/lib/utils";

const AXIS_LABEL: Record<AxisKey, string> = {
  founder: "Founder",
  market: "Market",
  idea_vs_market: "Idea vs Market",
};

function pct(n: number) {
  return `${Math.max(0, Math.min(1, n)) * 100}%`;
}

export function AxisMini({ label, axis }: { label: AxisKey; axis: Axis }) {
  const unscored = axis.basis === "not scored yet";
  return (
    <div className="min-w-[140px]">
      <div className="mb-1 flex items-baseline justify-between text-[10px] uppercase tracking-wider text-muted-foreground">
        <span>{AXIS_LABEL[label]}</span>
        {!unscored && <TrendArrow trend={axis.trend} />}
      </div>
      {unscored ? (
        <div className="font-mono text-base font-semibold text-muted-foreground">—</div>
      ) : (
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-base font-semibold tabular-nums">
            {axis.score.toFixed(2)}
          </span>
          <span className="font-mono text-[10px] text-muted-foreground tabular-nums">
            [{axis.band[0].toFixed(2)}–{axis.band[1].toFixed(2)}]
          </span>
        </div>
      )}
      {unscored ? (
        <div className="relative mt-1 h-1.5 w-full rounded-full bg-muted" />
      ) : (
        <RangeBar band={axis.band} score={axis.score} />
      )}
    </div>
  );
}

export function RangeBar({ band, score }: { band: [number, number]; score: number }) {
  const [lo, hi] = band;
  return (
    <div className="relative mt-1 h-1.5 w-full rounded-full bg-muted">
      <div
        className="absolute top-0 h-full rounded-full bg-primary/25"
        style={{ left: pct(lo), width: pct(Math.max(0.02, hi - lo)) }}
      />
      <div
        className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 rounded bg-primary"
        style={{ left: pct(score) }}
      />
    </div>
  );
}

export function TrendArrow({ trend }: { trend?: string }) {
  if (trend === "up")
    return (
      <span className="inline-flex items-center gap-0.5 text-[color:var(--trust-high)]">
        <ArrowUp className="h-3 w-3" />
        up
      </span>
    );
  if (trend === "down")
    return (
      <span className="inline-flex items-center gap-0.5 text-[color:var(--trust-flagged)]">
        <ArrowDown className="h-3 w-3" />
        down
      </span>
    );
  return (
    <span className="inline-flex items-center gap-0.5 text-muted-foreground">
      <Minus className="h-3 w-3" />
      flat
    </span>
  );
}

export function AxisCard({ label, axis }: { label: AxisKey; axis: Axis }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          {AXIS_LABEL[label]}
        </h3>
        <TrendArrow trend={axis.trend} />
      </div>
      <div className="mt-3 flex items-baseline gap-3">
        <span className="font-mono text-4xl font-semibold tabular-nums text-foreground">
          {axis.score.toFixed(2)}
        </span>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          confidence [{axis.band[0].toFixed(2)}–{axis.band[1].toFixed(2)}]
        </span>
      </div>
      <RangeBar band={axis.band} score={axis.score} />
      {axis.basis && (
        <p className="mt-2 font-mono text-[11px] text-muted-foreground">basis: {axis.basis}</p>
      )}
      {axis.stance && (
        <div className="mt-3 inline-block rounded border border-border bg-muted px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide">
          stance: {axis.stance}
        </div>
      )}
      {axis.rationale && (
        <p className="mt-3 text-sm leading-relaxed text-foreground/80">{axis.rationale}</p>
      )}
    </div>
  );
}

export function RecommendationChip({ rec }: { rec: string }) {
  const map: Record<string, { label: string; className: string }> = {
    invest_100k: {
      label: "INVEST $100K",
      className:
        "text-[color:var(--rec-invest)] bg-[color:var(--rec-invest-bg)] border-[color:var(--rec-invest)]/30",
    },
    escalate_to_human: {
      label: "ESCALATE",
      className:
        "text-[color:var(--rec-escalate)] bg-[color:var(--rec-escalate-bg)] border-[color:var(--rec-escalate)]/30",
    },
    pass: {
      label: "PASS",
      className:
        "text-[color:var(--rec-pass)] bg-[color:var(--rec-pass-bg)] border-[color:var(--rec-pass)]/30",
    },
  };
  const cfg = map[rec] ?? {
    label: rec.replace(/_/g, " ").toUpperCase(),
    className: "text-muted-foreground bg-muted border-border",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-1 font-mono text-[10px] font-semibold tracking-wider",
        cfg.className,
      )}
    >
      {cfg.label}
    </span>
  );
}