"use client";

import { useMemo, useState } from "react";
import type { ApplicationWithDetails } from "@/lib/types";
import { StatusBadge, TierBadge } from "./Badges";

type SortKey = "updated_at" | "fit_score" | "company" | "role" | "location";

const SORT_LABELS: Record<SortKey, string> = {
  updated_at: "Last updated",
  fit_score: "Fit score",
  company: "Company",
  role: "Role",
  location: "Location",
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
  }
}

// The cross-profile view (unlike JobsTable, which is already scoped to one profile by its tab)
// -- adds a Profile column and client-side sorting, since "everything, across every profile" is
// exactly the case where eyeballing an unsorted list stops working.
export default function ApplicationsTable({
  applications,
  selectedId,
  onSelect,
}: {
  applications: ApplicationWithDetails[];
  selectedId: string | null;
  onSelect: (row: ApplicationWithDetails) => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("updated_at");
  const [sortDesc, setSortDesc] = useState(true);

  const sorted = useMemo(() => {
    const copy = [...applications];
    copy.sort((a, b) => {
      const va = sortValue(a, sortKey);
      const vb = sortValue(b, sortKey);
      const cmp = va < vb ? -1 : va > vb ? 1 : 0;
      return sortDesc ? -cmp : cmp;
    });
    return copy;
  }, [applications, sortKey, sortDesc]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDesc((d) => !d);
    } else {
      setSortKey(key);
      setSortDesc(true);
    }
  }

  if (applications.length === 0) {
    return <p className="muted">No applications match the current filters.</p>;
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Profile</th>
            {(["company", "role", "fit_score", "location"] as SortKey[]).map((key) => (
              <th key={key} className="sortable" onClick={() => toggleSort(key)}>
                {SORT_LABELS[key] === "Fit score" ? "Fit" : SORT_LABELS[key]}
                {sortKey === key ? (sortDesc ? " ▼" : " ▲") : ""}
              </th>
            ))}
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
  );
}
