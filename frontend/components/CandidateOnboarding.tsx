"use client";

import { useState } from "react";
import { createCandidate, uploadResume } from "@/lib/api";
import type { CandidateProfile } from "@/lib/types";

export default function CandidateOnboarding({
  onDone,
}: {
  onDone: (candidate: CandidateProfile) => void;
}) {
  const [fullName, setFullName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName.trim()) {
      setError("Enter your name.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const candidate = await createCandidate(fullName.trim());
      if (file) {
        const parsed = await uploadResume(candidate.id, file);
        onDone(parsed);
      } else {
        onDone(candidate);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="onboarding-card panel">
      <h2>Set up your candidate profile</h2>
      <p className="muted">
        This creates a candidate record and, if you attach a resume, parses it into a structured,
        evidence-verified profile. You can upload a resume later too.
      </p>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="full-name">Full name</label>
          <input
            id="full-name"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Adi Rosenstock"
          />
        </div>
        <div className="field">
          <label htmlFor="resume">Resume (PDF, optional now)</label>
          <input
            id="resume"
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        {error && <div className="error-banner">{error}</div>}
        <button type="submit" className="primary" disabled={busy}>
          {busy ? "Setting up…" : "Continue"}
        </button>
      </form>
    </div>
  );
}
