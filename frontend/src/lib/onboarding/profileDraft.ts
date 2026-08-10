/**
 * The editable profile-details draft: what the form holds, how a saved snapshot
 * becomes one, how it is validated, and how it becomes a request payload.
 */

import type { FieldErrors } from "@/lib/api/fieldErrors"
import type { OnboardingSnapshot, ProfileDetailsPayload } from "@/lib/api/types"

export interface Identity {
  first_name: string
  last_name: string
  phone_number: string
  location: string
  title: string
}

export interface SocialLinksState {
  github_url: string
  linkedin_url: string
  portfolio_url: string
}

export interface EditableEducation {
  institution: string
  degree: string
  field: string
  start_date: string
  end_date: string
}

export interface EditableCertification {
  name: string
  issuer: string
  issued_at: string
  expires_at: string
}

export interface EditableEmployment {
  company_name: string
  title: string
  start_date: string
  end_date: string
  description: string
}

export interface EditableProject {
  /** null for a project added in the UI; set for one loaded from the backend. */
  project_id: number | null
  name: string
  summary: string
  github_url: string
  deployed_url: string
  technologies: string[]
}

/**
 * Everything the details form edits — exactly the eight fields the hook holds
 * in state. Read-only values that travel with the profile (`account_email`) and
 * upload plumbing (`source_resume_id`) are deliberately excluded: validation and
 * serialization have no business seeing them.
 */
export interface ProfileDraft {
  identity: Identity
  socialLinks: SocialLinksState
  summary: string
  technologies: string[]
  education: EditableEducation[]
  certifications: EditableCertification[]
  employment: EditableEmployment[]
  projects: EditableProject[]
}

/** A validated details section plus the mapping needed to place its errors. */
export type PreparedDetails = {
  payload: ProfileDetailsPayload
  projectPayloadIndexToUiIndex: number[]
}

export const EMPTY_IDENTITY: Identity = {
  first_name: "",
  last_name: "",
  phone_number: "",
  location: "",
  title: "",
}

export const EMPTY_LINKS: SocialLinksState = {
  github_url: "",
  linkedin_url: "",
  portfolio_url: "",
}

/** A draft with nothing filled in — the form's state before any snapshot loads. */
export const EMPTY_DRAFT: ProfileDraft = {
  identity: EMPTY_IDENTITY,
  socialLinks: EMPTY_LINKS,
  summary: "",
  technologies: [],
  education: [],
  certifications: [],
  employment: [],
  projects: [],
}

export const emptyEducation = (): EditableEducation => ({
  institution: "",
  degree: "",
  field: "",
  start_date: "",
  end_date: "",
})

export const emptyCertification = (): EditableCertification => ({
  name: "",
  issuer: "",
  issued_at: "",
  expires_at: "",
})

export const emptyEmployment = (): EditableEmployment => ({
  company_name: "",
  title: "",
  start_date: "",
  end_date: "",
  description: "",
})

export const emptyProject = (): EditableProject => ({
  project_id: null,
  name: "",
  summary: "",
  github_url: "",
  deployed_url: "",
  technologies: [],
})

// ── Internal rules ─────────────────────────────────────────────────────

const YEAR_OR_MONTH_RE = /^\d{4}(?:-(?:0[1-9]|1[0-2]))?$/
const MONTH_RE = /^\d{4}-(?:0[1-9]|1[0-2])$/

const emptyToNull = (value: string): string | null => value.trim() || null

/**
 * True when the user typed anything into the row (empty rows are dropped
 * silently). Note a project row holding only `project_id` counts as empty:
 * a number is neither a string nor an array.
 */
const hasContent = (row: object): boolean =>
  Object.values(row).some((value: unknown) =>
    typeof value === "string" ? value.trim() : Array.isArray(value) ? value.length : false,
  )

const hasValidYear = (value: string): boolean => {
  const year = Number(value.slice(0, 4))
  return year >= 1900 && year <= 2100
}

const validYearOrMonth = (value: string): boolean =>
  YEAR_OR_MONTH_RE.test(value) && hasValidYear(value)

const validMonth = (value: string): boolean => MONTH_RE.test(value) && hasValidYear(value)

/**
 * Whether an end date is definitely earlier than its start date. A year-only
 * value has intentionally unknown month precision, so within one year we only
 * reject when both sides carry months.
 */
const unambiguouslyPrecedes = (startValue: string, endValue: string): boolean => {
  const start = startValue.trim()
  const end = endValue.trim()
  if (!validYearOrMonth(start) || !validYearOrMonth(end)) return false
  const startYear = Number(start.slice(0, 4))
  const endYear = Number(end.slice(0, 4))
  if (endYear !== startYear) return endYear < startYear
  return start.length === 7 && end.length === 7 && end < start
}

// ── Lifecycle ──────────────────────────────────────────────────────────

/** The projects section alone — also used when reloading after a stale conflict. */
export const projectsFromSnapshot = (snapshot: OnboardingSnapshot): EditableProject[] =>
  snapshot.projects.map((project) => ({
    project_id: project.project_id,
    name: project.name,
    summary: project.summary ?? "",
    github_url: project.github_url ?? "",
    deployed_url: project.deployed_url ?? "",
    // Copied so form state never aliases the fetched snapshot.
    technologies: [...project.tech_stack],
  }))

/** Seed a fresh draft from a saved snapshot. */
export function draftFromSnapshot(snapshot: OnboardingSnapshot): ProfileDraft {
  const { profile } = snapshot
  return {
    identity: {
      first_name: profile.first_name ?? "",
      last_name: profile.last_name ?? "",
      phone_number: profile.phone_number ?? "",
      location: profile.location ?? "",
      title: profile.title ?? "",
    },
    socialLinks: {
      github_url: profile.social_links.github_url ?? "",
      linkedin_url: profile.social_links.linkedin_url ?? "",
      portfolio_url: profile.social_links.portfolio_url ?? "",
    },
    summary: profile.summary ?? "",
    technologies: [...profile.technologies],
    education: profile.education.map((item) => ({
      institution: item.institution ?? "",
      degree: item.degree ?? "",
      field: item.field ?? "",
      start_date: item.start_date ?? "",
      end_date: item.end_date ?? "",
    })),
    certifications: profile.certifications.map((item) => ({
      name: item.name ?? "",
      issuer: item.issuer ?? "",
      issued_at: item.issued_at ?? "",
      expires_at: item.expires_at ?? "",
    })),
    employment: snapshot.employment_history.map((item) => ({
      company_name: item.company_name,
      title: item.title,
      // API dates are YYYY-MM-DD; month inputs want YYYY-MM.
      start_date: item.start_date?.slice(0, 7) ?? "",
      end_date: item.end_date?.slice(0, 7) ?? "",
      description: item.description ?? "",
    })),
    projects: projectsFromSnapshot(snapshot),
  }
}

/**
 * Mirror of the backend's strict rules, for immediate field-level feedback.
 *
 * Key insertion order is load-bearing: the caller focuses the first key, so
 * errors are built identity -> education -> certifications -> employment ->
 * projects, and within identity in the order the fields appear on screen.
 */
export function validateDraft(draft: ProfileDraft): FieldErrors {
  const errors: FieldErrors = {}
  const { identity } = draft
  if (!identity.first_name.trim()) errors.first_name = "Enter your first name."
  if (!identity.last_name.trim()) errors.last_name = "Enter your last name."
  if (!identity.title.trim()) errors.title = "Enter your professional title."

  draft.education.forEach((row, index) => {
    if (!hasContent(row)) return
    if (!row.institution.trim()) errors[`education.${index}.institution`] = "Enter the institution."
    for (const field of ["start_date", "end_date"] as const) {
      const value = row[field].trim()
      if (value && !validYearOrMonth(value))
        errors[`education.${index}.${field}`] = "Use YYYY or YYYY-MM, with a year from 1900 to 2100."
    }
    if (unambiguouslyPrecedes(row.start_date, row.end_date))
      errors[`education.${index}.end_date`] =
        "The education end date cannot be before its start date."
  })

  draft.certifications.forEach((row, index) => {
    if (!hasContent(row)) return
    if (!row.name.trim()) errors[`certifications.${index}.name`] = "Enter the certification name."
    for (const field of ["issued_at", "expires_at"] as const) {
      const value = row[field].trim()
      if (value && !validYearOrMonth(value))
        errors[`certifications.${index}.${field}`] =
          "Use YYYY or YYYY-MM, with a year from 1900 to 2100."
    }
    if (unambiguouslyPrecedes(row.issued_at, row.expires_at))
      errors[`certifications.${index}.expires_at`] =
        "The expiration date cannot be before its issue date."
  })

  draft.employment.forEach((row, index) => {
    if (!hasContent(row)) return
    if (!row.company_name.trim())
      errors[`employment_history.${index}.company_name`] = "Enter the company."
    if (!row.title.trim()) errors[`employment_history.${index}.title`] = "Enter the job title."
    for (const field of ["start_date", "end_date"] as const) {
      const value = row[field].trim()
      if (value && !validMonth(value))
        errors[`employment_history.${index}.${field}`] =
          "Use YYYY-MM, with a year from 1900 to 2100."
    }
    if (validMonth(row.start_date) && validMonth(row.end_date) && row.end_date < row.start_date)
      errors[`employment_history.${index}.end_date`] =
        "The end month cannot be before the start month."
  })

  draft.projects.forEach((row, index) => {
    if (hasContent(row) && !row.name.trim())
      errors[`projects.${index}.name`] = "Enter the project name."
  })
  return errors
}

/** Serialize a draft into the complete `details` section of a PATCH. */
export function draftToPayload(draft: ProfileDraft): PreparedDetails {
  const projectRows = draft.projects
    .map((row, uiIndex) => ({ row, uiIndex }))
    .filter(({ row }) => hasContent(row))
  const payload: ProfileDetailsPayload = {
    first_name: emptyToNull(draft.identity.first_name),
    last_name: emptyToNull(draft.identity.last_name),
    phone_number: emptyToNull(draft.identity.phone_number),
    location: emptyToNull(draft.identity.location),
    title: emptyToNull(draft.identity.title),
    summary: emptyToNull(draft.summary),
    social_links: {
      github_url: emptyToNull(draft.socialLinks.github_url),
      linkedin_url: emptyToNull(draft.socialLinks.linkedin_url),
      portfolio_url: emptyToNull(draft.socialLinks.portfolio_url),
    },
    education: draft.education.filter(hasContent).map((row) => ({
      institution: row.institution.trim(),
      degree: emptyToNull(row.degree),
      field: emptyToNull(row.field),
      start_date: row.start_date || null,
      end_date: row.end_date || null,
    })),
    certifications: draft.certifications.filter(hasContent).map((row) => ({
      name: row.name.trim(),
      issuer: emptyToNull(row.issuer),
      issued_at: row.issued_at || null,
      expires_at: row.expires_at || null,
    })),
    employment_history: draft.employment.filter(hasContent).map((row) => ({
      company_name: row.company_name.trim(),
      title: row.title.trim(),
      start_date: row.start_date || null,
      end_date: row.end_date || null,
      description: emptyToNull(row.description),
    })),
    projects: projectRows.map(({ row }) => ({
      project_id: row.project_id,
      name: row.name.trim(),
      summary: emptyToNull(row.summary),
      github_url: emptyToNull(row.github_url),
      deployed_url: emptyToNull(row.deployed_url),
      technologies: row.technologies,
    })),
    technologies: draft.technologies,
  }
  // Blank drafts are filtered out of the payload, so a server error at payload
  // index N has to be mapped back to the row the user can see.
  return { payload, projectPayloadIndexToUiIndex: projectRows.map(({ uiIndex }) => uiIndex) }
}

/**
 * Trimmed, case-insensitively deduped append. Returns the original array
 * unchanged when the value is blank or already present.
 */
export function appendTechnology(technologies: string[], value: string): string[] {
  const technology = value.trim()
  if (!technology) return technologies
  return technologies.some((t) => t.toLowerCase() === technology.toLowerCase())
    ? technologies
    : [...technologies, technology]
}

/**
 * Path rewriter for `apiFieldErrors`: turns `projects.<payloadIndex>` into the
 * visible row index, since blank rows are dropped before sending. Always
 * returns a new array — the caller's `ApiError` must never be mutated.
 */
export function remapProjectRow(
  payloadIndexToUiIndex: number[],
): (path: Array<string | number>) => Array<string | number> {
  return (path) => {
    if (path[0] !== "projects" || typeof path[1] !== "number") return path
    const uiIndex = payloadIndexToUiIndex[path[1]]
    return uiIndex === undefined ? path : [path[0], uiIndex, ...path.slice(2)]
  }
}
