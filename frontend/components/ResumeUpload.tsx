"use client";

import { useRef, useState } from "react";
import { uploadResume } from "@/lib/api";
import type { CandidateProfile } from "@/lib/types";

export default function ResumeUpload({
  candidateId,
  hasResume,
  onUploaded,
}: {
  candidateId: string;
  hasResume: boolean;
  onUploaded: (candidate: CandidateProfile) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      onUploaded(await uploadResume(candidateId, file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ textAlign: "right" }}>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        aria-label="Resume PDF"
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
      <button onClick={() => inputRef.current?.click()} disabled={busy}>
        {busy ? "Parsing…" : hasResume ? "Re-upload resume" : "Upload resume"}
      </button>
      {error && <div className="muted">{error}</div>}
    </div>
  );
}
