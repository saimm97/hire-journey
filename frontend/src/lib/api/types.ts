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
  linkedin_data: Record<string, unknown> | null
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
}

/** A project payload for replacing the CV project set (mirror of ParsedProject). */
export interface ProjectInput {
  name: string
  summary?: string | null
  tech_stack?: string[]
  github_url?: string | null
  deployed_url?: string | null
}
