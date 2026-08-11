"use client";

import { useMemo, useState } from "react";
import type { ApplicationWithDetails } from "@/lib/types";
import { StatusBadge, TierBadge, VisaBadge } from "./Badges";

type SortKey = "updated_at" | "fit_score" | "company" | "role" | "location" | "visa";

const SORT_LABELS: Record<SortKey, string> = {
  updated_at: "Last updated",
  fit_score: "Fit score",
  company: "Company",
  role: "Role",
  location: "Location",
  visa: "Visa",
};

function sortValue(row: ApplicationWithDetails, key: SortKey): string | number {
  switch (key) {
    case "updated_at":
      return row.updated_at;
    case "fit_score":
      return row.fit_score?.overall_score ?? -1;
    case "company":
      return row.company.name.toLowerCase();
    case "role":
      return row.job.title.toLowerCase();
    case "location":
      return row.job.location?.toLowerCase() ?? "";
    case "visa":
      return row.job.visa_sponsorship ?? "";
  }
}

const VISA_FILTER_OPTIONS = [
  { value: "", label: "Any visa status" },
  { value: "likely_sponsors", label: "Likely sponsors" },
  { value: "likely_no_sponsorship", label: "Likely no sponsorship" },
  { value: "unknown", label: "Not checked yet" },
] as const;

// The cross-profile view (unlike JobsTable, which is already scoped to one profile by its tab)
// -- adds a Profile column and client-side sorting, since "everything, across every profile" is
// exactly the case where eyeballing an unsorted list stops working. `applications` here is
// already filtered server-side by the search/status controls above this table (see page.tsx);
// location/visa filter further, client-side, on top of that.
export default function ApplicationsTable({
  applications,
  selectedId,
  onSelect,
}: {
  applications: ApplicationWithDetails[];
  selectedId: string | null;
  onSelect: (row: ApplicationWithDetails) => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("fit_score");
  const [sortDesc, setSortDesc] = useState(true);
  const [locationFilter, setLocationFilter] = useState("");
  const [visaFilter, setVisaFilter] = useState("");

  const filtered = useMemo(() => {
    const needle = locationFilter.trim().toLowerCase();
    return applications.filter((row) => {
      if (needle && !(row.job.location ?? "").toLowerCase().includes(needle)) return false;
      if (visaFilter === "unknown" && row.job.visa_sponsorship !== null) return false;
      if (
        (visaFilter === "likely_sponsors" || visaFilter === "likely_no_sponsorship") &&
        row.job.visa_sponsorship !== visaFilter
      ) {
        return false;
      }
      return true;
    });
  }, [applications, locationFilter, visaFilter]);

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

      {filtered.length === 0 ? (
        <p className="muted">No applications match the current filters.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Profile</th>
                {(["company", "role", "fit_score", "location", "visa"] as SortKey[]).map(
                  (key) => (
                    <th key={key} className="sortable" onClick={() => toggleSort(key)}>
                      {key === "fit_score" ? "Fit" : SORT_LABELS[key]}
                      {sortKey === key ? (sortDesc ? " ▼" : " ▲") : ""}
                    </th>
                  )
                )}
                <th>Status</th>
                <th className="sortable" onClick={() => toggleSort("updated_at")}>
                  Updated{sortKey === "updated_at" ? (sortDesc ? " ▼" : " ▲") : ""}
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr
                  key={row.id}
                  className={row.id === selectedId ? "selected" : ""}
                  onClick={() => onSelect(row)}
                >
                  <td>
                    <span className="badge badge-status">{row.profile_display_name}</span>
                  </td>
                  <td>{row.company.name}</td>
                  <td>{row.job.title}</td>
                  <td>
                    {row.fit_score ? (
                      <TierBadge tier={row.fit_score.tier} score={row.fit_score.overall_score} />
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>{row.job.location ?? "—"}</td>
                  <td>
                    <VisaBadge
                      signal={row.job.visa_sponsorship}
                      evidence={row.job.visa_sponsorship_evidence}
                    />
                  </td>
                  <td>
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="muted">{new Date(row.updated_at).toLocaleDateString()}</td>
                  <td>
                    <a
                      href={row.job.job_url}
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
            Sorted by {SORT_LABELS[sortKey]} ({sortDesc ? "descending" : "ascending"}) -- click a
            column header to change.
          </p>
        </div>
      )}
    </div>
  );
}
