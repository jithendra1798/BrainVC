import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { FileText, Play } from "lucide-react";
import { api, type Claim, type TraceEntry } from "@/lib/api";
import { PageShell, EmptyState, LoadingRows } from "@/components/PageShell";
import { AxisCard, RecommendationChip } from "@/components/AxisMeter";
import { TrustBadge } from "@/components/TrustBadge";
import { ClaimDrawer } from "@/components/ClaimDrawer";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export const Route = createFileRoute("/opportunities/$id")({
  component: OpportunityPage,
});

function OpportunityPage() {
  const { id } = Route.useParams();
  const router = useRouter();
  const qc = useQueryClient();

  const opp = useQuery({ queryKey: ["opp", id], queryFn: () => api.opportunity(id) });
  const scores = useQuery({ queryKey: ["opp", id, "scores"], queryFn: () => api.scores(id) });
  const claims = useQuery({ queryKey: ["opp", id, "claims"], queryFn: () => api.claims(id) });
  const trace = useQuery({ queryKey: ["opp", id, "trace"], queryFn: () => api.trace(id) });

  const [drawerClaim, setDrawerClaim] = useState<Claim | null>(null);

  const [pipelineTimeline, setPipelineTimeline] = useState<TraceEntry[] | null>(null);
  const runPipeline = useMutation({
    mutationFn: () => api.runPipeline(id),
    onSuccess: (r) => {
      setPipelineTimeline(r.timeline ?? []);
      qc.invalidateQueries({ queryKey: ["opp", id] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
      router.invalidate();
      toast.success("Pipeline complete");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <>
      <PageShell
        eyebrow={
          <Link to="/" className="hover:text-foreground">
            ← Pipeline
          </Link>
        }
        title={opp.data?.company_name ?? "Opportunity"}
        subtitle={opp.data?.one_liner ?? undefined}
        actions={
          <>
            {opp.data?.recommendation && (
              <RecommendationChip rec={opp.data.recommendation} />
            )}
            <Button variant="outline" asChild>
              <Link to="/opportunities/$id/memo" params={{ id }}>
                <FileText className="mr-1 h-4 w-4" /> View memo
              </Link>
            </Button>
            <Button
              onClick={() => runPipeline.mutate()}
              disabled={runPipeline.isPending}
            >
              <Play className="mr-1 h-4 w-4" />
              {runPipeline.isPending ? "Running (~2m)…" : "Run full pipeline"}
            </Button>
          </>
        }
      >
        <section className="grid gap-4 md:grid-cols-3">
          {scores.isLoading &&
            Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="h-56 animate-pulse rounded-xl border border-border bg-muted/40"
              />
            ))}
          {scores.data && (
            <>
              <AxisCard label="founder" axis={scores.data.axes.founder} />
              <AxisCard label="market" axis={scores.data.axes.market} />
              <AxisCard label="idea_vs_market" axis={scores.data.axes.idea_vs_market} />
            </>
          )}
        </section>
        <p className="mt-2 font-mono text-[11px] text-muted-foreground">
          * three axes shown independently — never averaged into a single number.
        </p>

        <Tabs defaultValue="claims" className="mt-8">
          <TabsList>
            <TabsTrigger value="claims">
              Claims {claims.data ? `(${claims.data.claims.length})` : ""}
            </TabsTrigger>
            <TabsTrigger value="trace">Trace</TabsTrigger>
          </TabsList>
          <TabsContent value="claims" className="mt-4">
            {claims.isLoading && <LoadingRows />}
            {claims.data && claims.data.claims.length === 0 && (
              <EmptyState title="No claims yet" hint="Run the pipeline to extract claims." />
            )}
            {claims.data && claims.data.claims.length > 0 && (
              <div className="overflow-hidden rounded-xl border border-border bg-card">
                <div className="grid grid-cols-[140px_1fr_120px_200px] gap-4 border-b border-border bg-muted/40 px-5 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  <div>Category</div>
                  <div>Claim</div>
                  <div>Status</div>
                  <div>Trust</div>
                </div>
                {claims.data.claims.map((c) => (
                  <button
                    key={c.claim_id}
                    onClick={() => setDrawerClaim(c)}
                    className="grid w-full grid-cols-[140px_1fr_120px_200px] items-start gap-4 border-b border-border px-5 py-3 text-left transition-colors last:border-b-0 hover:bg-muted/40"
                  >
                    <div className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                      {c.category}
                    </div>
                    <div className="text-sm text-foreground">{c.text}</div>
                    <div className="font-mono text-[11px] text-muted-foreground">
                      {c.status}
                    </div>
                    <div>
                      <TrustBadge
                        level={c.trust.level}
                        value={c.trust.value}
                        rationale={c.trust.rationale}
                        verificationMethod={c.trust.verification_method}
                      />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </TabsContent>
          <TabsContent value="trace" className="mt-4">
            {trace.isLoading && <LoadingRows />}
            {trace.data && <TraceTimeline entries={trace.data.trace} />}
          </TabsContent>
        </Tabs>

        {pipelineTimeline && pipelineTimeline.length > 0 && (
          <section className="mt-8">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Latest pipeline run
            </h3>
            <TraceTimeline entries={pipelineTimeline} />
          </section>
        )}
      </PageShell>
      <ClaimDrawer
        claim={drawerClaim}
        open={drawerClaim !== null}
        onOpenChange={(v) => !v && setDrawerClaim(null)}
      />
    </>
  );
}

export function TraceTimeline({ entries }: { entries: TraceEntry[] }) {
  if (!entries || entries.length === 0) {
    return <EmptyState title="No trace entries" />;
  }
  return (
    <ol className="relative space-y-4 border-l border-border pl-6">
      {entries.map((e, i) => (
        <li key={i} className="relative">
          <span className="absolute -left-[27px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-primary bg-background" />
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider">
              {e.module}
            </span>
            <span className="text-sm font-medium text-foreground">{e.step}</span>
            {e.model && (
              <span className="font-mono text-[11px] text-muted-foreground">
                · {e.model}
              </span>
            )}
            <span className="ml-auto font-mono text-[11px] text-muted-foreground">
              {new Date(e.timestamp).toLocaleString()}
            </span>
          </div>
          <p className="mt-1 text-sm text-foreground/80">{e.summary}</p>
        </li>
      ))}
    </ol>
  );
}