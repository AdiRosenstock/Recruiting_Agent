"use client";

import { useState } from "react";
import type { SearchProfile } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Mirrors backend/scripts/seed_profiles.py's two default profiles exactly, so setting up from
// the UI produces the same config a fresh `python scripts/seed_profiles.py` run would.
const DEFAULT_PROFILES = [
  {
    profile_key: "startup_outreach",
    display_name: "Startup Outreach",
    outreach_enabled: true,
    config: {
      weights: {},
      role_filters: [
        "software engineer",
        "backend engineer",
        "founding engineer",
        "ai engineer",
        "data engineer",
        "ai infrastructure engineer",
        "product engineer",
        "forward deployed engineer",
      ],
      stage_filters: ["pre_seed", "seed", "series_a", "series_b"],
      location_filters: ["nyc", "new york", "remote"],
      notes: "Early-stage NYC startups, small technical teams. Outreach enabled.",
    },
  },
  {
    profile_key: "new_grad_2027",
    display_name: "New Grad 2027",
    outreach_enabled: false,
    config: {
      weights: { stage: 0.0, role: 0.25, experience: 0.2 },
      role_filters: [
        "software engineer",
        "backend engineer",
        "founding engineer",
        "ai engineer",
        "data engineer",
        "product engineer",
        "forward deployed engineer",
        "quant",
        "quantitative",
        "trading",
        "data analyst",
        "data scientist",
      ],
      stage_filters: [],
      location_filters: [],
      notes:
        "Wide-net new-grad 2027 search across company sizes, including finance/quant-adjacent roles given the Bloomberg background. Tracking only -- no outreach.",
    },
  },
];

export default function ProfileSetup({
  candidateId,
  onDone,
}: {
  candidateId: string;
  onDone: (profiles: SearchProfile[]) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      const created: SearchProfile[] = [];
      for (const profile of DEFAULT_PROFILES) {
        const response = await fetch(`${API_BASE_URL}/api/v1/search-profiles`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ candidate_id: candidateId, ...profile }),
        });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail ?? `Failed to create ${profile.display_name}`);
        }
        created.push(await response.json());
      }
      onDone(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel onboarding-card">
      <h2>Set up search profiles</h2>
      <p className="muted">
        Creates the two default agents: <strong>Startup Outreach</strong> (seed-Series B NYC,
        outreach enabled) and <strong>New Grad 2027</strong> (wide net, tracking only). You can
        tune weights/filters for either afterward.
      </p>
      {error && <div className="error-banner">{error}</div>}
      <button className="primary" onClick={handleCreate} disabled={busy}>
        {busy ? "Creating…" : "Create default profiles"}
      </button>
    </div>
  );
}
