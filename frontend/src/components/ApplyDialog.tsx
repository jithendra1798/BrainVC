import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { api } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

export function ApplyDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [result, setResult] = useState<{
    opportunity_id: string;
    evidence_created: number;
    evidence_deduplicated: number;
  } | null>(null);
  const [running, setRunning] = useState(false);

  const submit = useMutation({
    mutationFn: (form: FormData) => api.apply(form),
    onSuccess: (r) => {
      setResult(r);
      qc.invalidateQueries({ queryKey: ["pipeline"] });
      toast.success("Application received");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const runPipeline = useMutation({
    mutationFn: (id: string) => api.runPipeline(id),
    onSuccess: (_r, id) => {
      toast.success("Pipeline started");
      onOpenChange(false);
      navigate({ to: "/opportunities/$id", params: { id } });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    submit.mutate(fd);
  }

  function reset() {
    setResult(null);
    setRunning(false);
    submit.reset();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) reset();
        onOpenChange(v);
      }}
    >
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New inbound application</DialogTitle>
          <DialogDescription>
            Submit a company and its deck. Evidence is deduplicated on ingest.
          </DialogDescription>
        </DialogHeader>
        {!result ? (
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="company_name">Company</Label>
              <Input id="company_name" name="company_name" required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="founder_name">Founder</Label>
                <Input id="founder_name" name="founder_name" required />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="founder_email">Founder email</Label>
                <Input id="founder_email" name="founder_email" type="email" />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="one_liner">One-liner</Label>
              <Textarea id="one_liner" name="one_liner" rows={2} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="deck">Deck (.md or .pdf)</Label>
              <Input id="deck" name="deck" type="file" accept=".md,.pdf" required />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={submit.isPending}>
                {submit.isPending ? "Submitting…" : "Submit"}
              </Button>
            </DialogFooter>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="rounded-lg border border-border bg-muted/50 p-4 font-mono text-xs">
              <div>
                evidence_created:{" "}
                <span className="font-semibold text-foreground">{result.evidence_created}</span>
              </div>
              <div>
                evidence_deduplicated:{" "}
                <span className="font-semibold text-foreground">
                  {result.evidence_deduplicated}
                </span>
              </div>
              <div>opportunity_id: {result.opportunity_id}</div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() =>
                  navigate({
                    to: "/opportunities/$id",
                    params: { id: result.opportunity_id },
                  }).then(() => onOpenChange(false))
                }
              >
                View opportunity
              </Button>
              <Button
                disabled={running || runPipeline.isPending}
                onClick={() => {
                  setRunning(true);
                  runPipeline.mutate(result.opportunity_id);
                }}
              >
                {runPipeline.isPending ? "Starting…" : "Run full pipeline"}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}