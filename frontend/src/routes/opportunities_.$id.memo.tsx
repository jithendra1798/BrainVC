import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState, useMemo, Fragment } from "react";
import { AlertTriangle, Volume2 } from "lucide-react";
import { toast } from "sonner";
import { api, API_BASE, type Claim } from "@/lib/api";
import { PageShell, EmptyState, LoadingRows } from "@/components/PageShell";
import { RecommendationChip } from "@/components/AxisMeter";
import { TrustBadge } from "@/components/TrustBadge";
import { ClaimDrawer } from "@/components/ClaimDrawer";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/opportunities_/$id/memo")({
  component: MemoPage,
});

function MemoPage() {
  const { id } = Route.useParams();
  const q = useQuery({ queryKey: ["opp", id, "memo"], queryFn: () => api.memo(id) });
  const [drawer, setDrawer] = useState<Claim | null>(null);

  return (
    <>
      <PageShell
        eyebrow={
          <Link to="/opportunities/$id" params={{ id }} className="hover:text-foreground">
            ← Opportunity
          </Link>
        }
        title="Investment memo"
        subtitle="Every number visibly traces to a source."
        actions={<VoiceBrief id={id} />}
      >
        {q.isLoading && <LoadingRows />}
        {q.error && (
          <EmptyState title="No memo yet — run the pipeline" hint={(q.error as Error).message} />
        )}
        {q.data && (
          <MemoBody data={q.data} onOpenClaim={setDrawer} />
        )}
      </PageShell>
      <ClaimDrawer
        claim={drawer}
        open={drawer !== null}
        onOpenChange={(v) => !v && setDrawer(null)}
      />
    </>
  );
}

function VoiceBrief({ id }: { id: string }) {
  const [src, setSrc] = useState<string | null>(null);
  if (src) {
    return (
      <audio
        controls
        autoPlay
        src={src}
        className="h-9"
        onError={() => {
          toast.error("Voice briefing unavailable (ElevenLabs key not set)");
          setSrc(null);
        }}
      />
    );
  }
  return (
    <Button
      variant="outline"
      onClick={() => setSrc(`${API_BASE}/opportunities/${id}/brief.mp3`)}
    >
      <Volume2 className="mr-1 h-4 w-4" /> Voice briefing
    </Button>
  );
}

function MemoBody({
  data,
  onOpenClaim,
}: {
  data: { memo: import("@/lib/api").Memo; claims: Record<string, Claim> };
  onOpenClaim: (c: Claim) => void;
}) {
  const { memo, claims } = data;
  const claimOrder = useMemo(() => {
    const order: string[] = [];
    const seen = new Set<string>();
    const sources = [
      memo.recommendation_rationale,
      ...memo.sections.map((s) => s.markdown),
    ];
    for (const text of sources) {
      for (const m of text.matchAll(/\[claim:([a-f0-9-]+)\]/gi)) {
        const cid = m[1];
        if (!seen.has(cid)) {
          seen.add(cid);
          order.push(cid);
        }
      }
    }
    return order;
  }, [memo.sections, memo.recommendation_rationale]);
  const claimNumbers = useMemo(
    () => Object.fromEntries(claimOrder.map((cid, i) => [cid, i + 1])),
    [claimOrder],
  );

  return (
    <div className="mx-auto max-w-4xl">
      <section className="rounded-2xl border border-border bg-card p-6">
        <div className="mb-3 flex items-center gap-3">
          <RecommendationChip rec={memo.recommendation} />
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Recommendation
          </span>
        </div>
        <p className="text-base leading-relaxed text-foreground">
          {renderInline(memo.recommendation_rationale, claims, claimNumbers, onOpenClaim)}
        </p>
      </section>

      <div className="mt-8 space-y-8">
        {memo.sections.map((s, i) => (
          <section key={i}>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              {s.kind.replace(/_/g, " ")}
            </h2>
            <div className="prose-brainvc text-[15px] leading-relaxed text-foreground">
              <MarkdownWithClaims
                markdown={s.markdown}
                claims={claims}
                numbers={claimNumbers}
                onOpenClaim={onOpenClaim}
              />
            </div>
          </section>
        ))}
      </div>

      {memo.gaps && memo.gaps.length > 0 && (
        <section className="mt-8 rounded-xl border border-[color:var(--trust-medium)]/30 bg-[color:var(--trust-medium-bg)] p-5">
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-[color:var(--trust-medium)]" />
            <h3 className="text-sm font-semibold text-[color:var(--trust-medium)]">
              Declared gaps — not fabricated
            </h3>
          </div>
          <ul className="ml-6 list-disc space-y-1 text-sm text-foreground/85">
            {memo.gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function MarkdownWithClaims({
  markdown,
  claims,
  numbers,
  onOpenClaim,
}: {
  markdown: string;
  claims: Record<string, Claim>;
  numbers: Record<string, number>;
  onOpenClaim: (c: Claim) => void;
}) {
  // Render minimal markdown: split by blank lines into paragraphs,
  // preserve headings/lists, and swap [claim:UUID] tokens for TrustBadge chips.
  const blocks = markdown.split(/\n{2,}/);
  return (
    <>
      {blocks.map((block, i) => {
        const trimmed = block.trim();
        if (!trimmed) return null;
        if (/^#{1,6}\s/.test(trimmed)) {
          const level = trimmed.match(/^#+/)![0].length;
          const text = trimmed.replace(/^#+\s*/, "");
          const Tag = (`h${Math.min(level + 2, 6)}` as unknown) as keyof HTMLElementTagNameMap;
          return (
            <Tag key={i} className="mt-4 text-base font-semibold text-foreground">
              {renderInline(text, claims, numbers, onOpenClaim)}
            </Tag>
          );
        }
        if (/^[-*]\s/.test(trimmed)) {
          const items = trimmed.split(/\n/).map((l) => l.replace(/^[-*]\s+/, ""));
          return (
            <ul key={i} className="ml-6 list-disc space-y-1">
              {items.map((it, j) => (
                <li key={j}>{renderInline(it, claims, numbers, onOpenClaim)}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i} className="mb-3">
            {renderInline(trimmed, claims, numbers, onOpenClaim)}
          </p>
        );
      })}
    </>
  );
}

function renderInline(
  text: string,
  claims: Record<string, Claim>,
  numbers: Record<string, number>,
  onOpenClaim: (c: Claim) => void,
) {
  const parts: React.ReactNode[] = [];
  const regex = /\[claim:([a-f0-9-]+)\]/gi;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = regex.exec(text))) {
    if (m.index > last) parts.push(renderBold(text.slice(last, m.index)));
    const cid = m[1];
    const claim = claims[cid];
    if (claim) {
      parts.push(
        <button
          key={`c${k++}`}
          type="button"
          onClick={() => onOpenClaim(claim)}
          className="mx-0.5 align-baseline"
        >
          <TrustBadge
            level={claim.trust.level}
            value={claim.trust.value}
            rationale={claim.trust.rationale}
            verificationMethod={claim.trust.verification_method}
            numbered={numbers[cid]}
          />
        </button>,
      );
    } else {
      parts.push(
        <span key={`u${k++}`} className="font-mono text-xs text-muted-foreground">
          [claim missing]
        </span>,
      );
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(renderBold(text.slice(last)));
  return parts.map((p, i) => <Fragment key={i}>{p}</Fragment>);
}

function renderBold(text: string): React.ReactNode {
  const segments = text.split(/\*\*([^*]+)\*\*/g);
  if (segments.length === 1) return text;
  return segments.map((seg, i) =>
    i % 2 === 1 ? (
      <strong key={i} className="font-semibold text-foreground">
        {seg}
      </strong>
    ) : (
      <Fragment key={i}>{seg}</Fragment>
    ),
  );
}