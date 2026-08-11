import type { FitTier, VisaSponsorshipSignal } from "@/lib/types";

export function TierBadge({ tier, score }: { tier: FitTier; score: number }) {
  return (
    <span className={`badge badge-${tier}`}>
      {Math.round(score)} · {tier.replace("_", " ")}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <span className="badge badge-status">{status.replace(/_/g, " ")}</span>;
}

// A deterministic keyword signal (backend services/visa_sponsorship.py), not a confirmed fact --
// title says "likely" for exactly that reason; hover to see the matched phrase, which is the
// thing to actually verify against the real posting before assuming anything.
export function VisaBadge({
  signal,
  evidence,
}: {
  signal: VisaSponsorshipSignal | null;
  evidence?: string | null;
}) {
  if (signal === null) return <span className="muted">—</span>;
  const sponsors = signal === "likely_sponsors";
  return (
    <span
      className={`badge ${sponsors ? "badge-visa-yes" : "badge-visa-no"}`}
      title={evidence ?? undefined}
    >
      {sponsors ? "Likely sponsors" : "Likely no sponsorship"}
    </span>
  );
}
