/** Mirrors of the backend profile schemas (app/schemas/profile.py, project.py). */

export interface Profile {
  user_id: string
  first_name: string | null
  last_name: string | null
  email: string | null
  phone: string | null
  github_url: string | null
  portfolio_url: string | null
  minimum_salary: number | null
  tech_stack: string[] | null
  desired_role: string[]
  seniority_level: string[]
  location: string[]
  work_mode: string | null
  open_to_relocating: boolean
  source_resume_id: string | null
  created_at: string
  updated_at: string
}

export interface Project {
  project_id: string
  name: string
  summary: string | null
  tech_stack: string[] | null
  github_url: string | null
  deployed_url: string | null
  source: string
}

/** The onboarding snapshot returned by GET and POST /profile/cv. */
export interface ProfileSnapshot {
  profile: Profile
  resume_summary: string | null
  projects: Project[]
}

/** Editable, persisted candidate fields (mirror of backend ProfileUpdate). */
export interface ProfileUpdate {
  first_name?: string | null
  last_name?: string | null
  email?: string | null
  phone?: string | null
  github_url?: string | null
  portfolio_url?: string | null
  summary?: string | null
  tech_stack?: string[]
  /** Job-preference fields. Backed columns; the PATCH is partial (exclude_unset). */
  desired_role?: string[]
  seniority_level?: string[]
  minimum_salary?: number | null
  location?: string[]
  work_mode?: string | null
  open_to_relocating?: boolean
}

/** A project payload for replacing the whole project set (mirror of ProjectInput). */
export interface ProjectInput {
  name: string
  summary?: string | null
  tech_stack?: string[]
  github_url?: string | null
  deployed_url?: string | null
  /** Origin of the project, preserved across the full-set replace. */
  source: string
}
