import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Plus } from "lucide-react";
import { api, type PipelineOpportunity } from "@/lib/api";
import { PageShell, EmptyState, LoadingRows } from "@/components/PageShell";
import { AxisMini, RecommendationChip } from "@/components/AxisMeter";
import { Button } from "@/components/ui/button";
import { ApplyDialog } from "@/components/ApplyDialog";

export const Route = createFileRoute("/")({
  component: PipelinePage,
});

function TrackBadge({ track }: { track: string }) {
  const cls =
    track === "outbound"
      ? "bg-[color:var(--accent)] text-accent-foreground"
      : "bg-muted text-foreground";
  return (
    <span
      className={`rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${cls}`}
    >
      {track}
    </span>
  );
}

function StatusChip({ status }: { status: string }) {
  return (
    <span className="rounded-full border border-border bg-background px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
      {status.replace(/_/g, " ")}
    </span>
  );
}

function PipelinePage() {
  const [applyOpen, setApplyOpen] = useState(false);
  const q = useQuery({ queryKey: ["pipeline"], queryFn: api.pipeline });

  return (
    <>
      <PageShell
        eyebrow="Pipeline"
        title="Ranked opportunities"
        subtitle={
          q.data?.thesis?.name ? (
            <>
              Active thesis:{" "}
              <Link to="/thesis" className="font-medium text-foreground hover:underline">
                {q.data.thesis.name}
              </Link>
            </>
          ) : (
            "Loading active thesis…"
          )
        }
        actions={
          <Button onClick={() => setApplyOpen(true)} className="gap-1">
            <Plus className="h-4 w-4" /> New application
          </Button>
        }
      >
        {q.isLoading && <LoadingRows />}
        {q.error && (
          <EmptyState
            title="Could not load pipeline"
            hint={(q.error as Error).message}
            action={<Button onClick={() => q.refetch()}>Retry</Button>}
          />
        )}
        {q.data && q.data.opportunities.length === 0 && (
          <EmptyState
            title="No opportunities yet"
            hint="Submit an inbound application or scan a founder to get started."
          />
        )}
        {q.data && q.data.opportunities.length > 0 && (
          <>
            <div className="overflow-hidden rounded-xl border border-border bg-card">
              <div className="grid grid-cols-[minmax(220px,1.4fr)_repeat(3,minmax(160px,1fr))_auto] gap-4 border-b border-border bg-muted/40 px-5 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                <div>Company</div>
                <div>Founder</div>
                <div>Market</div>
                <div>Idea vs Market</div>
                <div className="text-right">Recommendation</div>
              </div>
              {q.data.opportunities.map((o) => (
                <PipelineRow key={o.opportunity_id} o={o} />
              ))}
            </div>
            <p className="mt-3 font-mono text-[11px] text-muted-foreground">
              * ordering is thesis-weighted; axes are never averaged.
            </p>
          </>
        )}
      </PageShell>
      <ApplyDialog open={applyOpen} onOpenChange={setApplyOpen} />
    </>
  );
}

function PipelineRow({ o }: { o: PipelineOpportunity }) {
  return (
    <Link
      to="/opportunities/$id"
      params={{ id: o.opportunity_id }}
      className="grid grid-cols-[minmax(220px,1.4fr)_repeat(3,minmax(160px,1fr))_auto] items-center gap-4 border-b border-border px-5 py-4 transition-colors last:border-b-0 hover:bg-muted/40"
    >
      <div>
        <div className="text-sm font-semibold text-foreground">{o.company_name}</div>
        <div className="mt-1 flex items-center gap-1.5">
          <TrackBadge track={o.track} />
          <StatusChip status={o.status} />
        </div>
      </div>
      <AxisMini label="founder" axis={o.axes.founder} />
      <AxisMini label="market" axis={o.axes.market} />
      <AxisMini label="idea_vs_market" axis={o.axes.idea_vs_market} />
      <div className="justify-self-end">
        <RecommendationChip rec={o.recommendation} />
      </div>
    </Link>
  );
}
