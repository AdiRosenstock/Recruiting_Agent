"use client";

import { useState } from "react";
import type { SearchProfile } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Mirrors backend/scripts/seed_profiles.py's default profile exactly, so setting up from the
// UI produces the same config a fresh `python scripts/seed_profiles.py` run would. Startup-only
// by design (see the root README's Roadmap) -- a since-removed "New Grad 2027" wide-net profile
// used to be seeded alongside this one; DEFAULT_PROFILE stays an object, not a hardcoded single
// POST call, so adding a second *startup-focused* profile later is a small object addition, not
// a rewrite.
const DEFAULT_PROFILE = {
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
};

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
      const response = await fetch(`${API_BASE_URL}/api/v1/search-profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_id: candidateId, ...DEFAULT_PROFILE }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail ?? `Failed to create ${DEFAULT_PROFILE.display_name}`);
      }
      onDone([await response.json()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel onboarding-card">
      <h2>Set up your search profile</h2>
      <p className="muted">
        Creates <strong>Startup Outreach</strong> -- seed-Series B NYC startups, small technical
        teams, outreach enabled. You can tune weights/filters afterward.
      </p>
      {error && <div className="error-banner">{error}</div>}
      <button className="primary" onClick={handleCreate} disabled={busy}>
        {busy ? "Creating…" : "Create search profile"}
      </button>
    </div>
  );
}
