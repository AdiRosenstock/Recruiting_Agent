import type { FitTier } from "@/lib/types";

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
