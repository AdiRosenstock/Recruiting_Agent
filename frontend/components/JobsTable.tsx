"use client";

import { useMemo, useState } from "react";
import type { JobWithScore } from "@/lib/types";
import { StatusBadge, TierBadge, VisaBadge } from "./Badges";

type SortKey = "company" | "role" | "fit" | "stage" | "location" | "status" | "visa";

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
    case "visa":
      return entry.job.visa_sponsorship ?? "";
  }
}

const VISA_FILTER_OPTIONS = [
  { value: "", label: "Any visa status" },
  { value: "likely_sponsors", label: "Likely sponsors" },
  { value: "likely_no_sponsorship", label: "Likely no sponsorship" },
  { value: "unknown", label: "Not checked yet" },
] as const;

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
  const [locationFilter, setLocationFilter] = useState("");
  const [visaFilter, setVisaFilter] = useState("");

  const filtered = useMemo(() => {
    const needle = locationFilter.trim().toLowerCase();
    return jobs.filter((entry) => {
      if (needle && !(entry.job.location ?? "").toLowerCase().includes(needle)) return false;
      if (visaFilter === "unknown" && entry.job.visa_sponsorship !== null) return false;
      if (
        (visaFilter === "likely_sponsors" || visaFilter === "likely_no_sponsorship") &&
        entry.job.visa_sponsorship !== visaFilter
      ) {
        return false;
      }
      return true;
    });
  }, [jobs, locationFilter, visaFilter]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) => {
      const va = sortValue(a, sortKey);
      const vb = sortValue(b, sortKey);
      const cmp = va < vb ? -1 : va > vb ? 1 : 0;
      return sortDesc ? -cmp : cmp;
    });
    return copy;
  }, [filtered, sortKey, sortDesc]);

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
    <div>
      <div className="filter-bar">
        <input
          type="search"
          placeholder="Filter by location…"
          aria-label="Filter by location"
          value={locationFilter}
          onChange={(e) => setLocationFilter(e.target.value)}
        />
        <select
          aria-label="Filter by visa sponsorship status"
          value={visaFilter}
          onChange={(e) => setVisaFilter(e.target.value)}
        >
          {VISA_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <span className="muted">{filtered.length} matching</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {headerLabel("company", "Company")}
              {headerLabel("role", "Role")}
              {headerLabel("fit", "Fit")}
              {headerLabel("stage", "Stage")}
              {headerLabel("location", "Location")}
              {headerLabel("visa", "Visa")}
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
                  <VisaBadge
                    signal={entry.job.visa_sponsorship}
                    evidence={entry.job.visa_sponsorship_evidence}
                  />
                </td>
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
          {filtered.length} job{filtered.length === 1 ? "" : "s"} -- click a column header to
          sort.
        </p>
      </div>
    </div>
  );
}
