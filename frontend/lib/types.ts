// Mirrors the backend's Pydantic response schemas (backend/app/schemas/*.py) -- kept as plain
// types, not generated, since the backend doesn't (yet) publish an OpenAPI-to-TS pipeline. Only
// the fields the dashboard actually reads are included.

export interface SkillClaim {
  id: string;
  skill_name: string;
  category: string;
  confidence: number;
  verified: boolean;
}

export interface CandidateProfile {
  id: string;
  full_name: string;
  email: string | null;
  primary_location: string | null;
  skills: SkillClaim[];
  active_resume_id: string | null;
}

export interface SearchProfileConfig {
  weights: Record<string, number>;
  role_filters: string[];
  stage_filters: string[];
  location_filters: string[];
  notes: string | null;
}

export interface SearchProfile {
  id: string;
  candidate_id: string;
  profile_key: string;
  display_name: string;
  outreach_enabled: boolean;
  config: SearchProfileConfig;
}

export interface CompanyRead {
  id: string;
  name: string;
  website: string | null;
  location: string | null;
  industry: string | null;
  description: string | null;
  funding_stage: string | null;
  employee_count: number | null;
}

export type VisaSponsorshipSignal = "likely_sponsors" | "likely_no_sponsorship";

export interface JobRead {
  id: string;
  company_id: string;
  title: string;
  location: string | null;
  job_url: string;
  description: string | null;
  technologies: string[];
  work_mode: string | null;
  deadline_date: string | null;
  status: string;
  visa_sponsorship: VisaSponsorshipSignal | null;
  visa_sponsorship_evidence: string | null;
  visa_sponsorship_checked_at: string | null;
}

export type FitTier = "excellent" | "strong" | "worth_reviewing" | "weak" | "ignore";

export interface FitScoreRead {
  id: string;
  overall_score: number;
  tier: FitTier;
  strengths: string[];
  gaps: string[];
  technical_match: number;
  role_match: number;
  ai_data_match: number;
  experience_match: number;
  stage_match: number;
  location_match: number;
  domain_match: number;
}

export const APPLICATION_STATUSES = [
  "DISCOVERED",
  "RESEARCHING",
  "REVIEW",
  "READY_TO_CONTACT",
  "CONTACTED",
  "RESPONDED",
  "INTERVIEW",
  "REJECTED",
  "ARCHIVED",
] as const;
export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number];

export interface JobWithScore {
  application_id: string;
  application_status: ApplicationStatus;
  job: JobRead;
  company: CompanyRead;
  fit_score: FitScoreRead | null;
}

export interface ApplicationRead {
  id: string;
  candidate_id: string;
  job_id: string;
  profile_id: string;
  contact_id: string | null;
  fit_score_id: string | null;
  outreach_message_id: string | null;
  status: ApplicationStatus;
  notes: string | null;
  contacted_at: string | null;
  responded_at: string | null;
}

// What GET /api/v1/applications returns -- the cross-profile "everything, searchable and
// filterable" view, unlike ApplicationRead's bare ids (used by GET/PATCH /applications/{id}).
export interface ApplicationWithDetails {
  id: string;
  candidate_id: string;
  profile_id: string;
  profile_key: string;
  profile_display_name: string;
  contact_id: string | null;
  fit_score_id: string | null;
  outreach_message_id: string | null;
  status: ApplicationStatus;
  notes: string | null;
  contacted_at: string | null;
  responded_at: string | null;
  updated_at: string;
  job: JobRead;
  company: CompanyRead;
  fit_score: FitScoreRead | null;
}

export interface CompanyResearchRead {
  id: string;
  company_id: string;
  fact_type: string;
  statement: string;
  is_inference: boolean;
  source_id: string | null;
  confidence: number | null;
}

export interface ContactRead {
  id: string;
  company_id: string;
  name: string;
  title: string | null;
  public_profile_url: string | null;
  email: string | null;
  priority_rank: number | null;
  rationale: string | null;
}

export type OutreachMessageType = "linkedin_full" | "linkedin_connection" | "email";

export interface OutreachMessageRead {
  id: string;
  candidate_id: string;
  job_id: string;
  contact_id: string | null;
  message_type: OutreachMessageType;
  content: string;
  personalization_rationale: string | null;
  is_user_edited: boolean;
  generated_by: string;
}

export interface OutreachGenerationResult {
  linkedin_full: OutreachMessageRead;
  linkedin_connection: OutreachMessageRead;
  email: OutreachMessageRead;
  warnings: string[];
}

export interface DiscoveryRunResult {
  profile_id: string;
  sources_run: string[];
  companies_upserted: number;
  jobs_upserted: number;
  warnings: string[];
}
