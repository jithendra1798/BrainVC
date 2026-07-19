import { AlertTriangle } from "lucide-react";
import type { TrustLevel } from "@/lib/api";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const styles: Record<TrustLevel, string> = {
  high: "text-[color:var(--trust-high)] bg-[color:var(--trust-high-bg)] border-[color:var(--trust-high)]/25",
  medium:
    "text-[color:var(--trust-medium)] bg-[color:var(--trust-medium-bg)] border-[color:var(--trust-medium)]/25",
  low: "text-[color:var(--trust-low)] bg-[color:var(--trust-low-bg)] border-[color:var(--trust-low)]/25",
  flagged:
    "text-[color:var(--trust-flagged)] bg-[color:var(--trust-flagged-bg)] border-[color:var(--trust-flagged)]/30",
};

const labels: Record<TrustLevel, string> = {
  high: "High trust",
  medium: "Medium trust",
  low: "Low trust",
  flagged: "Flagged",
};

export interface TrustBadgeProps {
  level: TrustLevel;
  value?: number;
  rationale?: string | null;
  verificationMethod?: string | null;
  size?: "sm" | "md";
  className?: string;
  numbered?: number;
}

export function TrustBadge({
  level,
  value,
  rationale,
  verificationMethod,
  size = "sm",
  className,
  numbered,
}: TrustBadgeProps) {
  const badge = (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border font-mono uppercase tracking-wide",
        size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs",
        styles[level],
        className,
      )}
    >
      {level === "flagged" && <AlertTriangle className="h-3 w-3" />}
      {numbered != null && <span className="font-semibold">[{numbered}]</span>}
      <span>{labels[level]}</span>
      {value != null && <span className="opacity-70">· {value.toFixed(2)}</span>}
    </span>
  );
  const hasTip = rationale || verificationMethod || value != null;
  if (!hasTip) return badge;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="cursor-help">{badge}</span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">
        <div className="space-y-1 text-xs">
          {value != null && (
            <div>
              <span className="text-muted-foreground">Trust value:</span>{" "}
              <span className="font-mono">{value.toFixed(3)}</span>
            </div>
          )}
          {rationale && <div>{rationale}</div>}
          {verificationMethod && (
            <div className="text-muted-foreground">
              Verified via <span className="font-mono">{verificationMethod}</span>
            </div>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}