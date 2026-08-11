// Thin typed wrapper around the FastAPI backend (backend/app/api/routers/*.py). Plain `fetch`,
// no data-fetching library (SWR/React Query) -- this is a personal, single-user dashboard, and
// each action below re-fetches what it needs afterward; that's simple enough not to need a
// caching layer. Every function throws `ApiError` on a non-2xx response, carrying the backend's
// `detail` message so the UI can show it.

import type {
  ApplicationRead,
  ApplicationStatus,
  CandidateProfile,
  CompanyResearchRead,
  ContactRead,
  DiscoveryRunResult,
  JobWithScore,
  OutreachGenerationResult,
  SearchProfile,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON -- keep statusText
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// --- Candidates ---

export function createCandidate(fullName: string): Promise<CandidateProfile> {
  return request("/api/v1/candidates", {
    method: "POST",
    body: JSON.stringify({ full_name: fullName }),
  });
}

export function getCandidate(candidateId: string): Promise<CandidateProfile> {
  return request(`/api/v1/candidates/${candidateId}`);
}

export async function uploadResume(candidateId: string, file: File): Promise<CandidateProfile> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/v1/candidates/${candidateId}/resume`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new ApiError(response.status, detail);
  }
  const result = await response.json();
  return result.profile as CandidateProfile;
}

// --- Search profiles ---

export function listSearchProfiles(candidateId: string): Promise<SearchProfile[]> {
  return request(`/api/v1/search-profiles?candidate_id=${candidateId}`);
}

export function getProfileJobs(profileId: string): Promise<JobWithScore[]> {
  return request(`/api/v1/search-profiles/${profileId}/jobs`);
}

// --- Discovery & scoring ---

export function runDiscovery(profileId: string): Promise<DiscoveryRunResult> {
  return request("/api/v1/discovery/run", {
    method: "POST",
    body: JSON.stringify({ profile_id: profileId }),
  });
}

export function scoreJob(jobId: string, candidateId: string, profileId: string) {
  return request(`/api/v1/jobs/${jobId}/score`, {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId, profile_id: profileId }),
  });
}

// --- Company research ---

export function runResearch(companyId: string): Promise<{ facts_created: number; inferences_created: number; warnings: string[] }> {
  return request(`/api/v1/companies/${companyId}/research/run`, { method: "POST" });
}

export function listResearch(companyId: string): Promise<CompanyResearchRead[]> {
  return request(`/api/v1/companies/${companyId}/research`);
}

// --- Contacts ---

export function listContacts(companyId: string): Promise<ContactRead[]> {
  return request(`/api/v1/companies/${companyId}/contacts`);
}

export function createContact(
  companyId: string,
  payload: { name: string; title?: string; public_profile_url?: string; email?: string }
): Promise<ContactRead> {
  return request(`/api/v1/companies/${companyId}/contacts`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- Applications & outreach ---

export function updateApplication(
  applicationId: string,
  payload: Partial<{ status: ApplicationStatus; notes: string; contact_id: string }>
): Promise<ApplicationRead> {
  return request(`/api/v1/applications/${applicationId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function generateOutreach(applicationId: string): Promise<OutreachGenerationResult> {
  return request(`/api/v1/applications/${applicationId}/outreach`, { method: "POST" });
}

export function editOutreachMessage(messageId: string, content: string) {
  return request(`/api/v1/outreach-messages/${messageId}`, {
    method: "PATCH",
    body: JSON.stringify({ content }),
  });
}
