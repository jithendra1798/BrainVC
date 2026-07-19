import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageShell, EmptyState, LoadingRows } from "@/components/PageShell";
import { RangeBar } from "@/components/AxisMeter";

export const Route = createFileRoute("/founders/$id")({
  component: FounderDetail,
});

function FounderDetail() {
  const { id } = Route.useParams();
  const q = useQuery({ queryKey: ["founder", id], queryFn: () => api.founder(id) });

  return (
    <PageShell
      eyebrow={
        <Link to="/founders" className="hover:text-foreground">
          ← Founders
        </Link>
      }
      title={q.data?.name ?? "Founder"}
    >
      {q.isLoading && <LoadingRows />}
      {q.error && <EmptyState title="Could not load founder" hint={(q.error as Error).message} />}
      {q.data && (
        <div className="grid gap-6 md:grid-cols-[320px_1fr]">
          <aside className="rounded-xl border border-border bg-card p-5">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Founder Score
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="font-mono text-4xl font-semibold tabular-nums">
                {q.data.founder_score.score.toFixed(2)}
              </span>
              <span className="font-mono text-[11px] text-muted-foreground">
                [{q.data.founder_score.band[0].toFixed(2)}–
                {q.data.founder_score.band[1].toFixed(2)}]
              </span>
            </div>
            <RangeBar band={q.data.founder_score.band} score={q.data.founder_score.score} />
            {q.data.github_handle && (
              <div className="mt-4 font-mono text-xs text-muted-foreground">
                github: @{q.data.github_handle}
              </div>
            )}

            <h3 className="mt-6 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Score history
            </h3>
            {q.data.score_history?.length ? (
              <ul className="space-y-1 font-mono text-xs">
                {q.data.score_history.map((h, i) => (
                  <li key={i} className="flex justify-between text-muted-foreground">
                    <span>{new Date(h.timestamp).toLocaleDateString()}</span>
                    <span className="text-foreground">{h.score.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">no history</p>
            )}
          </aside>
          <section>
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Evidence ({q.data.evidence?.length ?? 0})
            </h3>
            {(!q.data.evidence || q.data.evidence.length === 0) && (
              <EmptyState title="No evidence recorded" />
            )}
            <ul className="space-y-3">
              {q.data.evidence?.map((e, i) => (
                <li key={i} className="rounded-lg border border-border bg-card p-4">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                      {e.relation}
                    </span>
                    {e.source_type && (
                      <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                        {e.source_type}
                      </span>
                    )}
                    {e.retrieved_at && (
                      <span className="ml-auto font-mono text-[10px] text-muted-foreground">
                        {new Date(e.retrieved_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <blockquote className="border-l-2 border-primary/30 pl-3 text-sm italic text-foreground/80">
                    “{e.excerpt}”
                  </blockquote>
                  {e.source_ref && (
                    <div className="mt-2 font-mono text-[11px] text-muted-foreground">
                      {e.source_ref.startsWith("http") ? (
                        <a href={e.source_ref} target="_blank" rel="noreferrer" className="hover:underline">
                          {e.source_ref}
                        </a>
                      ) : (
                        e.source_ref
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </PageShell>
  );
}