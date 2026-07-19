import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { X } from "lucide-react";
import { api, type Thesis } from "@/lib/api";
import { PageShell, LoadingRows } from "@/components/PageShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export const Route = createFileRoute("/thesis")({
  component: ThesisPage,
});

function ThesisPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["thesis"], queryFn: api.thesis });
  const [draft, setDraft] = useState<Thesis | null>(null);

  useEffect(() => {
    if (q.data && !draft) setDraft(q.data);
  }, [q.data, draft]);

  const save = useMutation({
    mutationFn: (t: Thesis) => api.saveThesis(t),
    onSuccess: (t) => {
      setDraft(t);
      qc.invalidateQueries({ queryKey: ["thesis"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
      toast.success("Thesis saved");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <PageShell
      eyebrow="Configuration"
      title="Thesis"
      subtitle="Every score is computed through this lens."
      actions={
        <Button
          onClick={() => draft && save.mutate(draft)}
          disabled={!draft || save.isPending}
        >
          {save.isPending ? "Saving…" : "Save thesis"}
        </Button>
      }
    >
      {q.isLoading || !draft ? (
        <LoadingRows rows={6} />
      ) : (
        <div className="mx-auto max-w-3xl space-y-6 rounded-xl border border-border bg-card p-6">
          <div className="space-y-1.5">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
          </div>

          <TagField
            label="Sectors"
            values={draft.sectors ?? []}
            onChange={(v) => setDraft({ ...draft, sectors: v })}
          />
          <TagField
            label="Stages"
            values={draft.stages ?? []}
            onChange={(v) => setDraft({ ...draft, stages: v })}
          />
          <TagField
            label="Geographies"
            values={draft.geographies ?? []}
            onChange={(v) => setDraft({ ...draft, geographies: v })}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="check_size">Check size</Label>
              <Input
                id="check_size"
                value={String(draft.check_size ?? "")}
                onChange={(e) => setDraft({ ...draft, check_size: e.target.value })}
                className="font-mono"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Risk posture</Label>
              <Select
                value={draft.risk_posture}
                onValueChange={(v) => setDraft({ ...draft, risk_posture: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="back_potential_over_traction">
                    Back potential over traction
                  </SelectItem>
                  <SelectItem value="balanced">Balanced</SelectItem>
                  <SelectItem value="traction_first">Traction first</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <div className="mb-1 flex items-baseline justify-between">
              <Label>Axis weights</Label>
              <span className="font-mono text-[11px] text-muted-foreground">
                recommendation emphasis — does not merge axes
              </span>
            </div>
            <div className="space-y-4 rounded-lg border border-border bg-background p-4">
              {(["founder", "market", "idea_vs_market"] as const).map((k) => (
                <WeightRow
                  key={k}
                  label={k}
                  value={draft.axis_weights?.[k] ?? 0.33}
                  onChange={(v) =>
                    setDraft({
                      ...draft,
                      axis_weights: { ...draft.axis_weights, [k]: v },
                    })
                  }
                />
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-[color:var(--rec-invest)]/25 bg-[color:var(--rec-invest-bg)]/60 p-3 text-sm text-foreground">
            Every score is computed through this lens.
          </div>
        </div>
      )}
    </PageShell>
  );
}

function WeightRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-sm font-medium capitalize">{label.replace(/_/g, " ")}</span>
        <span className="font-mono text-xs tabular-nums text-muted-foreground">
          {value.toFixed(2)}
        </span>
      </div>
      <Slider
        min={0}
        max={1}
        step={0.01}
        value={[value]}
        onValueChange={(v) => onChange(v[0])}
      />
    </div>
  );
}

function TagField({
  label,
  values,
  onChange,
}: {
  label: string;
  values: string[];
  onChange: (v: string[]) => void;
}) {
  const [input, setInput] = useState("");
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <div className="flex flex-wrap items-center gap-1.5 rounded-md border border-border bg-background p-2">
        {values.map((v, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs"
          >
            {v}
            <button
              type="button"
              onClick={() => onChange(values.filter((_, j) => j !== i))}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === ",") && input.trim()) {
              e.preventDefault();
              onChange([...values, input.trim()]);
              setInput("");
            } else if (e.key === "Backspace" && !input && values.length) {
              onChange(values.slice(0, -1));
            }
          }}
          placeholder="Add and press Enter"
          className="flex-1 min-w-[120px] bg-transparent px-1 py-0.5 text-sm outline-none"
        />
      </div>
    </div>
  );
}