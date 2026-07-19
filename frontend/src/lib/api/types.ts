/** Mirrors of the backend onboarding schemas (app/schemas/profile.py, project.py). */

export type WorkMode = 'remote' | 'hybrid' | 'onsite'
export const WORK_MODES: WorkMode[] = ['remote', 'hybrid', 'onsite']

export type SeniorityLevel =
  | 'intern'
  | 'entry_level'
  | 'associate'
  | 'mid_level'
  | 'senior'
  | 'lead'
  | 'manager'
  | 'director'
export const SENIORITY_LEVELS: SeniorityLevel[] = [
  'intern',
  'entry_level',
  'associate',
  'mid_level',
  'senior',
  'lead',
  'manager',
  'director',
]

/** JSONB items on the profile; fields may be missing or null (lenient extraction). */
export type EducationItem = {
  institution?: string | null
  degree?: string | null
  field?: string | null
  start_date?: string | null
  end_date?: string | null
}

export type CertificationItem = {
  name?: string | null
  issuer?: string | null
  issued_at?: string | null
  expires_at?: string | null
}

/** Mirrors backend ProfileRead. */
export type Profile = {
  id: number
  user_id: number
  first_name: string | null
  last_name: string | null
  phone_number: string | null
  location: string | null
  social_links: Record<string, string>
  education: EducationItem[]
  certifications: CertificationItem[]
  title: string | null
  summary: string | null
  minimum_salary: number | null
  desired_locations: string[]
  desired_roles: string[]
  work_modes_preferred: string[]
  seniority_level: string | null
  technologies: string[]
  source_resume_id: number | null
  /** Read-only, from the authenticated User — never editable here. */
  account_email: string | null
  created_at: string
  updated_at: string
}

/** Mirrors backend ResumeMeta — metadata only, never the raw resume text. */
export type ResumeMeta = {
  id: number
  file_name: string
  created_at: string
  summary: string | null
}

/** Mirrors backend EmploymentRead. Dates are ISO YYYY-MM-DD (first of month). */
export type Employment = {
  id: number
  company_name: string
  title: string
  start_date: string | null
  end_date: string | null
  description: string | null
}

/** Mirrors backend ProjectRead. */
export type Project = {
  project_id: number
  name: string
  summary: string | null
  tech_stack: string[]
  github_url: string | null
  deployed_url: string | null
}

/** Mirrors backend OnboardingSnapshot — the one response shape for all onboarding calls. */
export type OnboardingSnapshot = {
  profile: Profile
  source_resume: ResumeMeta | null
  employment_history: Employment[]
  projects: Project[]
  onboarding_complete: boolean
}

// ── Write payloads (strict backend validation applies) ─────────────────

export type SocialLinksPayload = {
  github_url?: string | null
  linkedin_url?: string | null
  portfolio_url?: string | null
}

export type EducationEntry = {
  institution: string
  degree?: string | null
  field?: string | null
  start_date?: string | null
  end_date?: string | null
}

export type CertificationEntry = {
  name: string
  issuer?: string | null
  issued_at?: string | null
  expires_at?: string | null
}

export type EmploymentEntry = {
  company_name: string
  title: string
  start_date?: string | null
  end_date?: string | null
  description?: string | null
}

export type ProjectEntry = {
  /** Present -> edit of an owned project; absent -> a new one. */
  project_id?: number | null
  name: string
  summary?: string | null
  github_url?: string | null
  deployed_url?: string | null
  technologies: string[]
}

/** Mirrors backend ProfileDetailsUpdate — the complete details step (full replacement). */
export type ProfileDetailsPayload = {
  first_name: string | null
  last_name: string | null
  phone_number: string | null
  location: string | null
  title: string | null
  summary: string | null
  social_links: SocialLinksPayload
  education: EducationEntry[]
  certifications: CertificationEntry[]
  employment_history: EmploymentEntry[]
  projects: ProjectEntry[]
  technologies: string[]
}

/** Mirrors backend PreferencesUpdate. */
export type PreferencesPayload = {
  minimum_salary: number | null
  desired_roles: string[]
  desired_locations: string[]
  work_modes_preferred: WorkMode[]
  seniority_level: SeniorityLevel
}
