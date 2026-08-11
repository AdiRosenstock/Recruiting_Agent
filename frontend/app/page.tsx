"use client";

import { useEffect, useState } from "react";
import CandidateOnboarding from "@/components/CandidateOnboarding";
import JobDetailPanel from "@/components/JobDetailPanel";
import JobsTable from "@/components/JobsTable";
import ProfileSetup from "@/components/ProfileSetup";
import ResumeUpload from "@/components/ResumeUpload";
import { getCandidate, getProfileJobs, listSearchProfiles, runDiscovery, scoreJob } from "@/lib/api";
import type { ApplicationStatus, CandidateProfile, JobWithScore, SearchProfile } from "@/lib/types";

const CANDIDATE_ID_KEY = "recruiting_agent_candidate_id";

export default function DashboardPage() {
  // Lazily read localStorage once, synchronously, at first render -- avoids the
  // render-effect-setState-render cascade of doing it inside a useEffect. `null` on the server
  // render (no localStorage there) is fine: it matches what the client's first render sees
  // before hydration reconciles.
  const [savedCandidateId] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem(CANDIDATE_ID_KEY) : null
  );

  const [candidate, setCandidate] = useState<CandidateProfile | null>(null);
  const [loadingCandidate, setLoadingCandidate] = useState(savedCandidateId !== null);

  const [profiles, setProfiles] = useState<SearchProfile[]>([]);
  const [activeProfileId, setActiveProfileId] = useState<string | null>(null);

  const [jobs, setJobs] = useState<JobWithScore[]>([]);
  // Derived, not a separate synchronously-set flag: "loading" means the jobs we last loaded
  // don't correspond to the profile currently selected.
  const [loadedProfileId, setLoadedProfileId] = useState<string | null>(null);
  const jobsLoading = activeProfileId !== null && loadedProfileId !== activeProfileId;

  const [discoveryBusy, setDiscoveryBusy] = useState(false);
  const [scoringId, setScoringId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<JobWithScore | null>(null);

  // Load the saved candidate, if any, on mount.
  useEffect(() => {
    if (!savedCandidateId) return;
    let cancelled = false;
    getCandidate(savedCandidateId)
      .then((c) => {
        if (!cancelled) setCandidate(c);
      })
      .catch(() => {
        if (!cancelled) localStorage.removeItem(CANDIDATE_ID_KEY);
      })
      .finally(() => {
        if (!cancelled) setLoadingCandidate(false);
      });
    return () => {
      cancelled = true;
    };
  }, [savedCandidateId]);

  // Load profiles once we have a candidate.
  useEffect(() => {
    if (!candidate) return;
    let cancelled = false;
    listSearchProfiles(candidate.id)
      .then((loaded) => {
        if (cancelled) return;
        setProfiles(loaded);
        if (loaded.length > 0) setActiveProfileId((current) => current ?? loaded[0].id);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load profiles.");
      });
    return () => {
      cancelled = true;
    };
  }, [candidate]);

  // Load jobs whenever the active profile changes.
  useEffect(() => {
    if (!activeProfileId) return;
    let cancelled = false;
    getProfileJobs(activeProfileId)
      .then((loaded) => {
        if (cancelled) return;
        setJobs(loaded);
        setLoadedProfileId(activeProfileId);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load jobs.");
      });
    return () => {
      cancelled = true;
    };
  }, [activeProfileId]);

  function handleCandidateReady(c: CandidateProfile) {
    localStorage.setItem(CANDIDATE_ID_KEY, c.id);
    setCandidate(c);
  }

  async function handleRunDiscovery() {
    if (!activeProfileId) return;
    setDiscoveryBusy(true);
    setError(null);
    try {
      await runDiscovery(activeProfileId);
      setJobs(await getProfileJobs(activeProfileId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery failed.");
    } finally {
      setDiscoveryBusy(false);
    }
  }

  async function handleScore(entry: JobWithScore) {
    if (!candidate || !activeProfileId) return;
    setScoringId(entry.application_id);
    setError(null);
    try {
      await scoreJob(entry.job.id, candidate.id, activeProfileId);
      setJobs(await getProfileJobs(activeProfileId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scoring failed.");
    } finally {
      setScoringId(null);
    }
  }

  function handleStatusChange(applicationId: string, status: ApplicationStatus) {
    setJobs((prev) =>
      prev.map((j) => (j.application_id === applicationId ? { ...j, application_status: status } : j))
    );
    setSelected((prev) =>
      prev && prev.application_id === applicationId ? { ...prev, application_status: status } : prev
    );
  }

  if (loadingCandidate) {
    return (
      <div className="app-shell">
        <p className="spinner-inline">Loading…</p>
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="app-shell">
        <CandidateOnboarding onDone={handleCandidateReady} />
      </div>
    );
  }

  const activeProfile = profiles.find((p) => p.id === activeProfileId);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Recruiting Agent</h1>
          <div className="subtitle">
            {candidate.full_name}
            {candidate.skills.length > 0 && ` · ${candidate.skills.length} skills on file`}
          </div>
        </div>
        <ResumeUpload
          candidateId={candidate.id}
          hasResume={candidate.active_resume_id !== null}
          onUploaded={setCandidate}
        />
      </header>

      {error && <div className="error-banner">{error}</div>}

      {profiles.length === 0 ? (
        <ProfileSetup candidateId={candidate.id} onDone={setProfiles} />
      ) : (
        <>
          <div className="tabs">
            {profiles.map((p) => (
              <button
                key={p.id}
                className={`tab ${p.id === activeProfileId ? "active" : ""}`}
                onClick={() => setActiveProfileId(p.id)}
              >
                {p.display_name}
              </button>
            ))}
          </div>

          <div className="panel">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <span className="muted">
                {jobsLoading ? "Loading…" : `${jobs.length} tracked`}
              </span>
              <button className="primary" onClick={handleRunDiscovery} disabled={discoveryBusy}>
                {discoveryBusy ? "Running discovery…" : "Run discovery"}
              </button>
            </div>
            <JobsTable
              jobs={jobs}
              selectedId={selected?.application_id ?? null}
              onSelect={setSelected}
              onScore={handleScore}
              scoringId={scoringId}
            />
          </div>
        </>
      )}

      {selected && (
        <JobDetailPanel
          entry={selected}
          profile={activeProfile}
          onClose={() => setSelected(null)}
          onStatusChange={handleStatusChange}
        />
      )}
    </div>
  );
}
