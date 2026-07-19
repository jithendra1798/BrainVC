import type { ReactNode } from "react";

export function PageShell({
  children,
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  children: ReactNode;
  eyebrow?: ReactNode;
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <main className="mx-auto max-w-[1400px] px-6 py-8">
      {(title || eyebrow) && (
        <header className="mb-10 flex flex-wrap items-end justify-between gap-4">
          <div>
            {eyebrow && (
              <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
                {eyebrow}
              </div>
            )}
            {title && (
              <h1 className="text-4xl font-light tracking-tight text-foreground">{title}</h1>
            )}
            {subtitle && <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </main>
  );
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: import("react").ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-card/50 p-10 text-center">
      <p className="text-sm font-medium text-foreground">{title}</p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function LoadingRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-14 animate-pulse rounded-lg border border-border bg-muted/40"
        />
      ))}
    </div>
  );
}