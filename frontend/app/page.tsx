"use client";

import { useEffect, useState } from "react";
import ApplicationsTable from "@/components/ApplicationsTable";
import CandidateOnboarding from "@/components/CandidateOnboarding";
import JobDetailPanel from "@/components/JobDetailPanel";
import JobsTable from "@/components/JobsTable";
import ProfileSetup from "@/components/ProfileSetup";
import ResumeUpload from "@/components/ResumeUpload";
import {
  getCandidate,
  getProfileJobs,
  listApplications,
  listSearchProfiles,
  runDiscovery,
  scoreJob,
} from "@/lib/api";
import type {
  ApplicationStatus,
  ApplicationWithDetails,
  CandidateProfile,
  JobWithScore,
  SearchProfile,
} from "@/lib/types";
import { APPLICATION_STATUSES } from "@/lib/types";

const CANDIDATE_ID_KEY = "recruiting_agent_candidate_id";
// A sentinel `activeProfileId` value meaning "the cross-profile view," alongside real profile
// UUIDs -- keeps the existing per-profile tab/loading logic untouched rather than threading a
// separate "which view" state through everything below.
const ALL_APPLICATIONS_TAB = "__all__";

function toJobWithScore(row: ApplicationWithDetails): JobWithScore {
  // JobDetailPanel is written against JobsTable's per-profile shape; the cross-profile view
  // reuses it as-is via this adapter rather than forking the whole detail panel for one extra
  // column of context (profile name), which the caller already has separately.
  return {
    application_id: row.id,
    application_status: row.status,
    job: row.job,
    company: row.company,
    fit_score: row.fit_score,
  };
}

export default function DashboardPage() {
  // NOT read synchronously via a lazy useState initializer: `typeof window !== "undefined"` is
  // true during the client's *first* render too (before hydration finishes), not just on later
  // renders -- so a lazy initializer branching on it disagrees with the server's render (which
  // always sees `undefined`) and React logs a hydration mismatch. Every render before hydration
  // completes, server and client, has to render the *same* thing: start both at "unknown /
  // loading", and only read localStorage in a `useEffect` (runs client-only, strictly after
  // hydration), same as React's own "synchronizing with a browser API" guidance.
  const [savedCandidateId, setSavedCandidateId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  const [candidate, setCandidate] = useState<CandidateProfile | null>(null);
  // Derived, not stored: "loading" means we haven't hydrated yet, or we have a saved id whose
  // fetch hasn't finished (`candidateFetchDone` is set only in that fetch's `.finally()`, a
  // genuine async continuation, not a synchronous effect-body branch). Before hydration this is
  // always `true` on both server and client, which is what avoids the mismatch.
  const [candidateFetchDone, setCandidateFetchDone] = useState(false);
  const loadingCandidate = !hydrated || (savedCandidateId !== null && !candidateFetchDone);

  useEffect(() => {
    // react-hooks/set-state-in-effect assumes this state could instead be computed during
    // render; it can't be here -- localStorage is a browser API with no server-side
    // equivalent, so reading it during render is exactly what produced the hydration mismatch
    // this effect exists to avoid. This is React's own documented exception: "synchronizing
    // with an external system" (https://react.dev/learn/you-might-not-need-an-effect).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSavedCandidateId(localStorage.getItem(CANDIDATE_ID_KEY));
    setHydrated(true);
  }, []);

  const [profiles, setProfiles] = useState<SearchProfile[]>([]);
  const [activeProfileId, setActiveProfileId] = useState<string | null>(null);
  const activeProfile = profiles.find((p) => p.id === activeProfileId);

  const [jobs, setJobs] = useState<JobWithScore[]>([]);
  // Derived, not a separate synchronously-set flag: "loading" means the jobs we last loaded
  // don't correspond to the profile currently selected.
  const [loadedProfileId, setLoadedProfileId] = useState<string | null>(null);
  const jobsLoading = activeProfileId !== null && loadedProfileId !== activeProfileId;

  const [discoveryBusy, setDiscoveryBusy] = useState(false);
  const [scoringId, setScoringId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<JobWithScore | null>(null);
  const [selectedProfileForDetail, setSelectedProfileForDetail] = useState<
    SearchProfile | undefined
  >(undefined);

  // The cross-profile "All Applications" view -- separate from the per-profile `jobs` state
  // above so switching back to a profile tab doesn't need to re-fetch it.
  const [applications, setApplications] = useState<ApplicationWithDetails[]>([]);
  const [applicationsLoading, setApplicationsLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "">("");
  const [searchQuery, setSearchQuery] = useState("");

  // Load the saved candidate, if any, once we know (post-hydration) whether one was saved.
  useEffect(() => {
    if (!hydrated || !savedCandidateId) return;
    let cancelled = false;
    getCandidate(savedCandidateId)
      .then((c) => {
        if (!cancelled) setCandidate(c);
      })
      .catch(() => {
        if (!cancelled) localStorage.removeItem(CANDIDATE_ID_KEY);
      })
      .finally(() => {
        if (!cancelled) setCandidateFetchDone(true);
      });
    return () => {
      cancelled = true;
    };
  }, [hydrated, savedCandidateId]);

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

  // Load jobs whenever the active profile changes. Skipped for the "All Applications" sentinel
  // -- that tab loads from the separate applications effect below instead.
  useEffect(() => {
    if (!activeProfileId || activeProfileId === ALL_APPLICATIONS_TAB) return;
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

  // Load the cross-profile applications list whenever that tab is active, or its filters
  // change. Debounced on the free-text query only -- status changes are infrequent clicks, not
  // keystrokes, so they don't need the delay.
  useEffect(() => {
    if (!candidate || activeProfileId !== ALL_APPLICATIONS_TAB) return;
    let cancelled = false;
    const handle = setTimeout(
      () => {
        setApplicationsLoading(true);
        listApplications(candidate.id, {
          status: statusFilter || undefined,
          q: searchQuery.trim() || undefined,
        })
          .then((loaded) => {
            if (!cancelled) setApplications(loaded);
          })
          .catch((err) => {
            if (!cancelled) {
              setError(err instanceof Error ? err.message : "Failed to load applications.");
            }
          })
          .finally(() => {
            if (!cancelled) setApplicationsLoading(false);
          });
      },
      searchQuery ? 300 : 0
    );
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [candidate, activeProfileId, statusFilter, searchQuery]);

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
    setApplications((prev) =>
      prev.map((a) => (a.id === applicationId ? { ...a, status } : a))
    );
    setSelected((prev) =>
      prev && prev.application_id === applicationId ? { ...prev, application_status: status } : prev
    );
  }

  function handleSelectApplication(row: ApplicationWithDetails) {
    setSelectedProfileForDetail(profiles.find((p) => p.id === row.profile_id));
    setSelected(toJobWithScore(row));
  }

  function handleSelectProfileJob(entry: JobWithScore) {
    setSelectedProfileForDetail(activeProfile);
    setSelected(entry);
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
            <button
              className={`tab ${activeProfileId === ALL_APPLICATIONS_TAB ? "active" : ""}`}
              onClick={() => setActiveProfileId(ALL_APPLICATIONS_TAB)}
            >
              All Applications
            </button>
          </div>

          {activeProfileId === ALL_APPLICATIONS_TAB ? (
            <div className="panel">
              <div className="filter-bar">
                <input
                  type="search"
                  placeholder="Search by job title or company…"
                  aria-label="Search applications by job title or company"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <select
                  aria-label="Filter by status"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as ApplicationStatus | "")}
                >
                  <option value="">All statuses</option>
                  {APPLICATION_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
                <span className="muted">
                  {applicationsLoading ? "Loading…" : `${applications.length} matching`}
                </span>
              </div>
              <ApplicationsTable
                applications={applications}
                selectedId={selected?.application_id ?? null}
                onSelect={handleSelectApplication}
              />
            </div>
          ) : (
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
                onSelect={handleSelectProfileJob}
                onScore={handleScore}
                scoringId={scoringId}
              />
            </div>
          )}
        </>
      )}

      {selected && (
        <JobDetailPanel
          entry={selected}
          profile={selectedProfileForDetail}
          onClose={() => setSelected(null)}
          onStatusChange={handleStatusChange}
        />
      )}
    </div>
  );
}
