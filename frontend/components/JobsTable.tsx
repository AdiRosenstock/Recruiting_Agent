"use client";

import { useMemo, useState } from "react";
import type { JobWithScore } from "@/lib/types";
import { StatusBadge, TierBadge } from "./Badges";

type SortKey = "company" | "role" | "fit" | "stage" | "location" | "status";

function sortValue(entry: JobWithScore, key: SortKey): string | number {
  switch (key) {
    case "company":
      return entry.company.name.toLowerCase();
    case "role":
      return entry.job.title.toLowerCase();
    case "fit":
      return entry.fit_score?.overall_score ?? -1;
    case "stage":
      return entry.company.funding_stage ?? "";
    case "location":
      return entry.job.location?.toLowerCase() ?? "";
    case "status":
      return entry.application_status;
  }
}

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
  // Defaults to highest fit first -- matches the API's own default ordering, so sorting only
  // changes anything once you actually click a header.
  const [sortKey, setSortKey] = useState<SortKey>("fit");
  const [sortDesc, setSortDesc] = useState(true);

  const sorted = useMemo(() => {
    const copy = [...jobs];
    copy.sort((a, b) => {
      const va = sortValue(a, sortKey);
      const vb = sortValue(b, sortKey);
      const cmp = va < vb ? -1 : va > vb ? 1 : 0;
      return sortDesc ? -cmp : cmp;
    });
    return copy;
  }, [jobs, sortKey, sortDesc]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDesc((d) => !d);
    } else {
      setSortKey(key);
      setSortDesc(true);
    }
  }

  if (jobs.length === 0) {
    return (
      <p className="muted">
        Nothing tracked yet. Run discovery above, or add a company/job manually via the API.
      </p>
    );
  }

  function headerLabel(key: SortKey, label: string) {
    return (
      <th className="sortable" onClick={() => toggleSort(key)}>
        {label}
        {sortKey === key ? (sortDesc ? " ▼" : " ▲") : ""}
      </th>
    );
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {headerLabel("company", "Company")}
            {headerLabel("role", "Role")}
            {headerLabel("fit", "Fit")}
            {headerLabel("stage", "Stage")}
            {headerLabel("location", "Location")}
            {headerLabel("status", "Status")}
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((entry) => (
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
      <p className="muted" style={{ marginTop: 8 }}>
        {jobs.length} job{jobs.length === 1 ? "" : "s"} -- click a column header to sort.
      </p>
    </div>
  );
}
