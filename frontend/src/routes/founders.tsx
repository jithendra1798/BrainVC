import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Copy, Github, Radar } from "lucide-react";
import { api, type ColdStart, type Founder } from "@/lib/api";
import { PageShell, EmptyState, LoadingRows } from "@/components/PageShell";
import { RangeBar } from "@/components/AxisMeter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export const Route = createFileRoute("/founders")({
  component: FoundersPage,
});

function FoundersPage() {
  const qc = useQueryClient();
  const founders = useQuery({ queryKey: ["founders"], queryFn: api.founders });
  const [handle, setHandle] = useState("");
  const [scan, setScan] = useState<ColdStart | null>(null);

  const scanMut = useMutation({
    mutationFn: (h: string) => api.scanFounder(h),
    onSuccess: (r) => {
      setScan(r.cold_start);
      qc.invalidateQueries({ queryKey: ["founders"] });
      toast.success("Founder scanned");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const [outreach, setOutreach] = useState<{ subject: string; body: string } | null>(null);
  const activate = useMutation({
    mutationFn: (id: string) => api.activateFounder(id),
    onSuccess: (r) => setOutreach(r.outreach),
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <>
      <PageShell
        eyebrow="Outbound"
        title="Founders pool"
        subtitle="Scan founders from the wild. Activate them into your outbound queue."
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (handle.trim()) scanMut.mutate(handle.trim());
          }}
          className="mb-8 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-card p-4"
        >
          <div className="flex-1">
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Scan founder by GitHub handle
            </label>
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">
                <Github className="h-4 w-4" />
              </span>
              <Input
                value={handle}
                onChange={(e) => setHandle(e.target.value)}
                placeholder="octocat"
                className="font-mono"
              />
            </div>
          </div>
          <Button type="submit" disabled={scanMut.isPending} className="gap-1">
            <Radar className="h-4 w-4" />
            {scanMut.isPending ? "Scanning…" : "Scan founder"}
          </Button>
        </form>

        {scan && (
          <section className="mb-8 rounded-xl border border-border bg-card p-5">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Cold-start assessment
            </h3>
            <div className="space-y-3">
              {scan.dimensions.map((d) => (
                <div key={d.name}>
                  <div className="mb-1 flex items-baseline justify-between">
                    <span className="text-sm font-medium">{d.name}</span>
                    <span className="font-mono text-sm tabular-nums">
                      {d.score.toFixed(2)}
                    </span>
                  </div>
                  <RangeBar band={[Math.max(0, d.score - 0.05), Math.min(1, d.score + 0.05)]} score={d.score} />
                  <p className="mt-1 text-xs text-muted-foreground">{d.rationale}</p>
                </div>
              ))}
            </div>
            {scan.known_unknowns && scan.known_unknowns.length > 0 && (
              <div className="mt-5 rounded-lg border border-[color:var(--trust-medium)]/30 bg-[color:var(--trust-medium-bg)] p-4">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[color:var(--trust-medium)]">
                  What we could NOT observe
                </h4>
                <ul className="ml-5 list-disc space-y-1 text-sm text-foreground/85">
                  {scan.known_unknowns.map((u, i) => (
                    <li key={i}>{u}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {founders.isLoading && <LoadingRows rows={4} />}
        {founders.data && founders.data.founders.length === 0 && (
          <EmptyState title="No founders yet" hint="Scan a GitHub handle to add one." />
        )}
        {founders.data && founders.data.founders.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {founders.data.founders.map((f) => (
              <FounderCard
                key={f.founder_id}
                f={f}
                onActivate={() => activate.mutate(f.founder_id)}
                activating={activate.isPending}
              />
            ))}
          </div>
        )}
      </PageShell>

      <Dialog open={outreach !== null} onOpenChange={(v) => !v && setOutreach(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Outreach draft</DialogTitle>
          </DialogHeader>
          {outreach && (
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Subject
                </label>
                <div className="rounded-md border border-border bg-muted/40 p-3 font-mono text-sm">
                  {outreach.subject}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Body
                </label>
                <div className="max-h-[45vh] overflow-y-auto whitespace-pre-wrap rounded-md border border-border bg-muted/40 p-3 text-sm leading-relaxed">
                  {outreach.body}
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `Subject: ${outreach.subject}\n\n${outreach.body}`,
                    );
                    toast.success("Copied to clipboard");
                  }}
                >
                  <Copy className="mr-1 h-4 w-4" /> Copy
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

function FounderCard({
  f,
  onActivate,
  activating,
}: {
  f: Founder;
  onActivate: () => void;
  activating: boolean;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <Link
            to="/founders/$id"
            params={{ id: f.founder_id }}
            className="text-sm font-semibold text-foreground hover:underline"
          >
            {f.name}
          </Link>
          {f.github_handle && (
            <div className="mt-0.5 flex items-center gap-1 font-mono text-[11px] text-muted-foreground">
              <Github className="h-3 w-3" /> @{f.github_handle}
            </div>
          )}
        </div>
        <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          {f.evidence_count} evidence
        </span>
      </div>
      <div className="mt-4">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Founder Score
        </div>
        <div className="mt-1 flex items-baseline gap-2">
          <span className="font-mono text-3xl font-semibold tabular-nums">
            {f.founder_score.score.toFixed(2)}
          </span>
          <span className="font-mono text-[11px] text-muted-foreground">
            [{f.founder_score.band[0].toFixed(2)}–{f.founder_score.band[1].toFixed(2)}]
          </span>
        </div>
        <RangeBar band={f.founder_score.band} score={f.founder_score.score} />
      </div>
      <Sparkline history={f.score_history ?? []} />
      <Button
        onClick={onActivate}
        disabled={activating}
        size="sm"
        className="mt-4 w-full"
        variant="outline"
      >
        {activating ? "Activating…" : "Activate"}
      </Button>
    </div>
  );
}

function Sparkline({ history }: { history: { timestamp: string; score: number }[] }) {
  if (!history || history.length < 2) {
    return (
      <div className="mt-3 h-8 rounded bg-muted/40 text-center font-mono text-[10px] leading-8 text-muted-foreground">
        no history yet
      </div>
    );
  }
  const W = 240;
  const H = 32;
  const min = Math.min(...history.map((h) => h.score));
  const max = Math.max(...history.map((h) => h.score));
  const range = max - min || 1;
  const step = W / (history.length - 1);
  const points = history
    .map((h, i) => `${(i * step).toFixed(1)},${(H - ((h.score - min) / range) * H).toFixed(1)}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 h-8 w-full text-primary">
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}