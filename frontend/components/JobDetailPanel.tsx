"use client";

import { useEffect, useState } from "react";
import {
  checkVisaSponsorship,
  createContact,
  editOutreachMessage,
  generateOutreach,
  getLatestOutreach,
  listContacts,
  listResearch,
  runResearch,
  updateApplication,
} from "@/lib/api";
import {
  APPLICATION_STATUSES,
  type ApplicationStatus,
  type CompanyResearchRead,
  type ContactRead,
  type JobRead,
  type JobWithScore,
  type OutreachGenerationResult,
  type OutreachMessageRead,
  type SearchProfile,
} from "@/lib/types";
import { StatusBadge, TierBadge, VisaBadge } from "./Badges";

export default function JobDetailPanel({
  entry,
  profile,
  candidateId,
  onClose,
  onStatusChange,
  onJobUpdated,
}: {
  entry: JobWithScore;
  profile: SearchProfile | undefined;
  candidateId: string;
  onClose: () => void;
  onStatusChange: (applicationId: string, status: ApplicationStatus) => void;
  onJobUpdated: (job: JobRead) => void;
}) {
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-header">
          <div>
            <h2 style={{ margin: 0 }}>{entry.company.name}</h2>
            <div className="muted">{entry.job.title}</div>
          </div>
          <button className="drawer-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="section">
          <h3>Fit</h3>
          <FitBreakdown entry={entry} />
        </div>

        <div className="section">
          <h3>Company</h3>
          <CompanyInfo entry={entry} />
        </div>

        <div className="section">
          <h3>Visa sponsorship</h3>
          <VisaSection job={entry.job} onJobUpdated={onJobUpdated} />
        </div>

        <div className="section">
          <h3>Research</h3>
          <ResearchSection companyId={entry.company.id} />
        </div>

        <div className="section">
          <h3>Contact</h3>
          <ContactsSection companyId={entry.company.id} />
        </div>

        {profile?.outreach_enabled && (
          <div className="section">
            <h3>Outreach</h3>
            <OutreachSection
              applicationId={entry.application_id}
              candidateId={candidateId}
              jobId={entry.job.id}
            />
          </div>
        )}

        <div className="section">
          <h3>Status</h3>
          <StatusControls entry={entry} onStatusChange={onStatusChange} />
        </div>
      </div>
    </>
  );
}

function FitBreakdown({ entry }: { entry: JobWithScore }) {
  const score = entry.fit_score;
  if (!score) return <p className="muted">Not scored yet.</p>;
  return (
    <>
      <p>
        <TierBadge tier={score.tier} score={score.overall_score} />
      </p>
      {score.strengths.length > 0 && (
        <ul className="list-plain">
          {score.strengths.map((s, i) => (
            <li key={i} className="strength-item">
              {s}
            </li>
          ))}
        </ul>
      )}
      {score.gaps.length > 0 && (
        <ul className="list-plain">
          {score.gaps.map((g, i) => (
            <li key={i} className="gap-item">
              {g}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function CompanyInfo({ entry }: { entry: JobWithScore }) {
  const { company } = entry;
  return (
    <>
      {company.description && <p>{company.description}</p>}
      <p className="muted">
        {[company.industry, company.funding_stage, company.employee_count ? `${company.employee_count} employees` : null]
          .filter(Boolean)
          .join(" · ") || "No further details on file."}
      </p>
      {company.website && (
        <p>
          <a href={company.website} target="_blank" rel="noreferrer">
            {company.website} ↗
          </a>
        </p>
      )}
    </>
  );
}

function VisaSection({
  job,
  onJobUpdated,
}: {
  job: JobRead;
  onJobUpdated: (job: JobRead) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheck() {
    setBusy(true);
    setError(null);
    try {
      onJobUpdated(await checkVisaSponsorship(job.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Check failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <p>
        <VisaBadge signal={job.visa_sponsorship} />
      </p>
      {job.visa_sponsorship_evidence && (
        <p className="muted">Matched: {job.visa_sponsorship_evidence}</p>
      )}
      <p className="muted">
        A deterministic keyword scan of the posting text -- a lead to verify on the actual
        listing, never a confirmed fact.
      </p>
      {error && <div className="error-banner">{error}</div>}
      <button onClick={handleCheck} disabled={busy}>
        {busy
          ? "Checking…"
          : job.visa_sponsorship_checked_at
            ? "Re-check"
            : "Check visa sponsorship"}
      </button>
    </>
  );
}

function ResearchSection({ companyId }: { companyId: string }) {
  const [facts, setFacts] = useState<CompanyResearchRead[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listResearch(companyId)
      .then(setFacts)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load research."));
  }, [companyId]);

  async function handleRun() {
    setBusy(true);
    setError(null);
    try {
      await runResearch(companyId);
      setFacts(await listResearch(companyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button onClick={handleRun} disabled={busy}>
        {busy ? "Researching…" : facts && facts.length > 0 ? "Re-run research" : "Run research"}
      </button>
      {error && <div className="error-banner">{error}</div>}
      {facts && facts.length > 0 && (
        <ul className="list-plain" style={{ marginTop: 10 }}>
          {facts.map((f) => (
            <li key={f.id} className={f.is_inference ? "inference-item" : "fact-item"}>
              {f.statement}
            </li>
          ))}
        </ul>
      )}
      {facts && facts.length === 0 && (
        <p className="muted">No research yet -- needs a company website on file.</p>
      )}
    </>
  );
}

function ContactsSection({ companyId }: { companyId: string }) {
  const [contacts, setContacts] = useState<ContactRead[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listContacts(companyId)
      .then(setContacts)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load contacts."));
  }, [companyId]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createContact(companyId, {
        name: name.trim(),
        title: title.trim() || undefined,
        public_profile_url: url.trim() || undefined,
      });
      setContacts(await listContacts(companyId));
      setName("");
      setTitle("");
      setUrl("");
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add contact.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error && <div className="error-banner">{error}</div>}
      {contacts && contacts.length > 0 && (
        <ul className="list-plain">
          {contacts
            .slice()
            .sort((a, b) => (a.priority_rank ?? 99) - (b.priority_rank ?? 99))
            .map((c) => (
              <li key={c.id}>
                <strong>{c.name}</strong>
                {c.title ? ` — ${c.title}` : ""}
                {c.public_profile_url && (
                  <>
                    {" "}
                    <a href={c.public_profile_url} target="_blank" rel="noreferrer">
                      profile ↗
                    </a>
                  </>
                )}
                <div className="muted">{c.rationale}</div>
              </li>
            ))}
        </ul>
      )}
      {!showForm && (
        <button onClick={() => setShowForm(true)}>
          {contacts && contacts.length > 0 ? "Add another contact" : "Add a contact"}
        </button>
      )}
      {showForm && (
        <form onSubmit={handleAdd}>
          <div className="form-row">
            <input
              placeholder="Name"
              aria-label="Contact name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              placeholder="Title"
              aria-label="Contact title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="form-row">
            <input
              placeholder="Public profile URL (optional)"
              aria-label="Public profile URL"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Saving…" : "Save contact"}
          </button>{" "}
          <button type="button" onClick={() => setShowForm(false)}>
            Cancel
          </button>
        </form>
      )}
    </>
  );
}

function OutreachSection({
  applicationId,
  candidateId,
  jobId,
}: {
  applicationId: string;
  candidateId: string;
  jobId: string;
}) {
  const [result, setResult] = useState<OutreachGenerationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load whatever was already drafted (including a prior hand edit) on open -- generating is a
  // separate, explicit action, not something opening the drawer should trigger or overwrite.
  useEffect(() => {
    let cancelled = false;
    getLatestOutreach(candidateId, jobId)
      .then((loaded) => {
        if (!cancelled) setResult(loaded);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load outreach.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [candidateId, jobId]);

  async function handleGenerate() {
    // Regenerating creates a fresh set of three drafts (and any hand edits on the current ones
    // stop being "the latest" shown, even though the old rows aren't deleted) -- confirm first
    // rather than silently discarding what's on screen, which is exactly what this UI used to
    // do with no warning at all.
    if (result && !window.confirm("Generate a new draft? Your current draft won't be shown anymore (it isn't deleted, just no longer the latest).")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setResult(await generateOutreach(applicationId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Outreach generation failed.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <>
      <button onClick={handleGenerate} disabled={busy}>
        {busy ? "Drafting…" : result ? "Regenerate" : "Generate outreach"}
      </button>
      {error && <div className="error-banner">{error}</div>}
      {result && result.warnings.length > 0 && (
        <div className="error-banner">{result.warnings.join(" ")}</div>
      )}
      {result && (
        <>
          <p className="muted" style={{ marginTop: 10 }}>
            {result.linkedin_full.personalization_rationale}
          </p>
          <MessageVariant
            key={result.linkedin_full.id}
            label="LinkedIn message"
            message={result.linkedin_full}
          />
          <MessageVariant
            key={result.linkedin_connection.id}
            label="Connection note"
            message={result.linkedin_connection}
          />
          <MessageVariant key={result.email.id} label="Email" message={result.email} />
        </>
      )}
    </>
  );
}

function MessageVariant({ label, message }: { label: string; message: OutreachMessageRead }) {
  const [content, setContent] = useState(message.content);
  const [saved, setSaved] = useState(true);
  const [copyLabel, setCopyLabel] = useState("Copy");

  async function handleSave() {
    await editOutreachMessage(message.id, content);
    setSaved(true);
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(content);
    setCopyLabel("Copied!");
    setTimeout(() => setCopyLabel("Copy"), 1500);
  }

  return (
    <div className="message-variant">
      <div className="message-variant-header">
        <strong>{label}</strong>
        <span>
          <button onClick={handleCopy}>{copyLabel}</button>{" "}
          <button onClick={handleSave} disabled={saved} className={saved ? "" : "primary"}>
            {saved ? "Saved" : "Save edits"}
          </button>
        </span>
      </div>
      <textarea
        aria-label={`${label} message content`}
        value={content}
        onChange={(e) => {
          setContent(e.target.value);
          setSaved(false);
        }}
      />
    </div>
  );
}

function StatusControls({
  entry,
  onStatusChange,
}: {
  entry: JobWithScore;
  onStatusChange: (applicationId: string, status: ApplicationStatus) => void;
}) {
  const [busy, setBusy] = useState(false);

  async function handleChange(status: ApplicationStatus) {
    setBusy(true);
    try {
      await updateApplication(entry.application_id, { status });
      onStatusChange(entry.application_id, status);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="form-row" style={{ alignItems: "center" }}>
      <StatusBadge status={entry.application_status} />
      <select
        aria-label="Application status"
        value={entry.application_status}
        disabled={busy}
        onChange={(e) => handleChange(e.target.value as ApplicationStatus)}
      >
        {APPLICATION_STATUSES.map((s) => (
          <option key={s} value={s}>
            {s.replace(/_/g, " ")}
          </option>
        ))}
      </select>
    </div>
  );
}
