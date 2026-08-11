"use client";

import type { JobWithScore } from "@/lib/types";
import { StatusBadge, TierBadge } from "./Badges";

export default function JobsTable({
  jobs,
  selectedId,
  onSelect,
  onScore,
  scoringId,
}: {
  jobs: JobWithScore[];
  selectedId: string | null;
  onSelect: (job: JobWithScore) => void;
  onScore: (job: JobWithScore) => void;
  scoringId: string | null;
}) {
  if (jobs.length === 0) {
    return (
      <p className="muted">
        Nothing tracked yet. Run discovery above, or add a company/job manually via the API.
      </p>
    );
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Role</th>
            <th>Fit</th>
            <th>Stage</th>
            <th>Location</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((entry) => (
            <tr
              key={entry.application_id}
              className={entry.application_id === selectedId ? "selected" : ""}
              onClick={() => onSelect(entry)}
            >
              <td>{entry.company.name}</td>
              <td>{entry.job.title}</td>
              <td>
                {entry.fit_score ? (
                  <TierBadge tier={entry.fit_score.tier} score={entry.fit_score.overall_score} />
                ) : (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onScore(entry);
                    }}
                    disabled={scoringId === entry.application_id}
                  >
                    {scoringId === entry.application_id ? "Scoring…" : "Score"}
                  </button>
                )}
              </td>
              <td>{entry.company.funding_stage ?? "—"}</td>
              <td>{entry.job.location ?? "—"}</td>
              <td>
                <StatusBadge status={entry.application_status} />
              </td>
              <td>
                <a
                  href={entry.job.job_url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  Open ↗
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
