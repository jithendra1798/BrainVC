import type { Claim } from "@/lib/api";
import { TrustBadge } from "./TrustBadge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ExternalLink } from "lucide-react";

function RelationChip({ relation }: { relation: string }) {
  const map: Record<string, string> = {
    asserts: "bg-muted text-foreground",
    supports: "bg-[color:var(--trust-high-bg)] text-[color:var(--trust-high)]",
    contradicts: "bg-[color:var(--trust-flagged-bg)] text-[color:var(--trust-flagged)]",
  };
  return (
    <span
      className={`rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide ${
        map[relation] ?? "bg-muted text-muted-foreground"
      }`}
    >
      {relation}
    </span>
  );
}

export function ClaimDrawer({
  claim,
  open,
  onOpenChange,
}: {
  claim: Claim | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        {claim && (
          <>
            <SheetHeader>
              <div className="flex items-center gap-2">
                <span className="rounded bg-muted px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider">
                  {claim.category}
                </span>
                <TrustBadge
                  level={claim.trust.level}
                  value={claim.trust.value}
                  rationale={claim.trust.rationale}
                  verificationMethod={claim.trust.verification_method}
                />
              </div>
              <SheetTitle className="mt-2 text-left text-base font-semibold leading-snug">
                {claim.text}
              </SheetTitle>
              <SheetDescription className="text-left font-mono text-[11px]">
                status: {claim.status} · claim_id: {claim.claim_id}
              </SheetDescription>
            </SheetHeader>
            <div className="mt-6">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Evidence ({claim.evidence?.length ?? 0})
              </h4>
              {(!claim.evidence || claim.evidence.length === 0) && (
                <div className="rounded border border-dashed border-border p-4 text-sm text-muted-foreground">
                  No evidence recorded.
                </div>
              )}
              <ul className="space-y-3">
                {claim.evidence?.map((e, i) => {
                  const isUrl = e.source_ref?.startsWith("http");
                  return (
                    <li key={i} className="rounded-lg border border-border bg-card p-3">
                      <div className="mb-1 flex items-center gap-2">
                        <RelationChip relation={e.relation} />
                        {e.source_type && (
                          <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase text-muted-foreground">
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
                          {isUrl ? (
                            <a
                              href={e.source_ref}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-primary hover:underline"
                            >
                              {e.source_ref}
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          ) : (
                            <span>{e.source_ref}</span>
                          )}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}