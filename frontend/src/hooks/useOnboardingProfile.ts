"use client"

import {
  useCallback,
  useEffect,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react"

import { ApiError } from "@/lib/api/client"
import { getOnboarding, updateProfile, uploadCv as uploadCvRequest } from "@/lib/api/profile"
import type { OnboardingSnapshot, ProfileDetailsPayload } from "@/lib/api/types"
import { COMPLETED_DESTINATION } from "@/lib/onboarding/routing"
import type { ToastData } from "@/components/onboarding/Toast"

export type OnboardingStatus = "loading" | "empty" | "parsing" | "ready" | "load_error"

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

export interface ListController<T> {
  items: T[]
  add: () => void
  update: (index: number, patch: Partial<T>) => void
  remove: (index: number) => void
  fieldPath: (index: number, field: keyof T) => string
  fieldError: (index: number, field: keyof T) => string | undefined
  rowError: (index: number) => string | undefined
}

export type FieldErrors = Record<string, string>

const EMPTY_IDENTITY: Identity = {
  first_name: "",
  last_name: "",
  phone_number: "",
  location: "",
  title: "",
}

const EMPTY_LINKS: SocialLinksState = { github_url: "", linkedin_url: "", portfolio_url: "" }

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024
const ALLOWED_EXTENSIONS = [".pdf", ".docx"]
const YEAR_OR_MONTH_RE = /^\d{4}(?:-(?:0[1-9]|1[0-2]))?$/
const MONTH_RE = /^\d{4}-(?:0[1-9]|1[0-2])$/

const emptyToNull = (value: string): string | null => value.trim() || null

const messageOf = (error: unknown): string =>
  error instanceof ApiError ? error.message : "Something went wrong. Try again."

/** An error toast that also surfaces the support reference on a 500. */
const errorToast = (error: unknown): ToastData => ({
  variant: "error",
  message: messageOf(error),
  requestId: error instanceof ApiError ? error.requestId : undefined,
})

/** True when the user typed anything into the row (empty rows are dropped silently). */
const hasContent = (row: object): boolean =>
  Object.values(row).some((value: unknown) =>
    typeof value === "string" ? value.trim() : Array.isArray(value) ? value.length : false,
  )

const pathKey = (path: Array<string | number>): string => path.join(".")

const hasValidYear = (value: string): boolean => {
  const year = Number(value.slice(0, 4))
  return year >= 1900 && year <= 2100
}

const validYearOrMonth = (value: string): boolean =>
  YEAR_OR_MONTH_RE.test(value) && hasValidYear(value)

const validMonth = (value: string): boolean => MONTH_RE.test(value) && hasValidYear(value)

const unambiguouslyPrecedes = (startValue: string, endValue: string): boolean => {
  const start = startValue.trim()
  const end = endValue.trim()
  if (!validYearOrMonth(start) || !validYearOrMonth(end)) return false
  const startYear = Number(start.slice(0, 4))
  const endYear = Number(end.slice(0, 4))
  if (endYear !== startYear) return endYear < startYear
  return start.length === 7 && end.length === 7 && end < start
}

function focusFirstError(errors: FieldErrors): void {
  if (typeof document === "undefined") return
  const firstPath = Object.keys(errors)[0]
  if (!firstPath) return
  const schedule =
    window.requestAnimationFrame ??
    ((callback: FrameRequestCallback) => window.setTimeout(callback, 0))
  schedule(() => {
    const field = Array.from(
      document.querySelectorAll<HTMLElement>("[data-field-path]"),
    ).find((element) => element.dataset.fieldPath === firstPath)
    field?.focus()
  })
}

/** A validated details section plus the mapping needed to place its errors. */
export type PreparedDetails = {
  payload: ProfileDetailsPayload
  projectPayloadIndexToUiIndex: number[]
}

function apiFieldErrors(
  error: ApiError,
  projectPayloadIndexToUiIndex: number[] = [],
): FieldErrors {
  const errors: FieldErrors = {}
  for (const field of error.fields) {
    const path = field.path[0] === "details" ? field.path.slice(1) : [...field.path]
    if (!path.length) continue
    if (path[0] === "projects" && typeof path[1] === "number") {
      const uiIndex = projectPayloadIndexToUiIndex[path[1]]
      if (uiIndex !== undefined) path[1] = uiIndex
    }
    const key = pathKey(path)
    errors[key] ??= field.message
  }
  return errors
}

const editableProjects = (snapshot: OnboardingSnapshot): EditableProject[] =>
  snapshot.projects.map((project) => ({
    project_id: project.project_id,
    name: project.name,
    summary: project.summary ?? "",
    github_url: project.github_url ?? "",
    deployed_url: project.deployed_url ?? "",
    technologies: [...project.tech_stack],
  }))

const isProjectErrorPath = (path: string): boolean =>
  path === "projects" || path.startsWith("projects.")

function validateFile(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext)))
    return "That needs to be a PDF or DOCX."
  if (file.size > MAX_UPLOAD_BYTES) return "That file's over 5MB. Try a smaller PDF or DOCX."
  return null
}

/** Local list state with the add/update/remove surface every repeatable editor needs. */
function useListController<T>(
  makeEmpty: () => T,
  pathPrefix: string,
  fieldErrors: FieldErrors,
  setFieldErrors: Dispatch<SetStateAction<FieldErrors>>,
): ListController<T> & {
  setItems: (items: T[]) => void
} {
  const [items, setItems] = useState<T[]>([])
  const fieldPath = useCallback(
    (index: number, field: keyof T) => `${pathPrefix}.${index}.${String(field)}`,
    [pathPrefix],
  )
  return {
    items,
    setItems,
    add: useCallback(() => setItems((prev) => [...prev, makeEmpty()]), [makeEmpty]),
    update: useCallback(
      (index: number, patch: Partial<T>) => {
        setItems((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))
        setFieldErrors((prev) => {
          const next = { ...prev }
          delete next[`${pathPrefix}.${index}`]
          for (const field of Object.keys(patch)) {
            delete next[`${pathPrefix}.${index}.${field}`]
          }
          return next
        })
      },
      [pathPrefix, setFieldErrors],
    ),
    remove: useCallback(
      (index: number) => {
        setItems((prev) => prev.filter((_, i) => i !== index))
        // Removing a row shifts every following index, so discard the section's
        // stale server paths rather than highlighting the wrong entry.
        setFieldErrors((prev) =>
          Object.fromEntries(
            Object.entries(prev).filter(([path]) => !path.startsWith(`${pathPrefix}.`)),
          ),
        )
      },
      [pathPrefix, setFieldErrors],
    ),
    fieldPath,
    fieldError: (index, field) => fieldErrors[fieldPath(index, field)],
    rowError: (index) => fieldErrors[`${pathPrefix}.${index}`],
  }
}

export interface OnboardingProfileOptions {
  /** Redirect completed users away (wizard behavior). Pass false on the edit page. */
  guardCompleted?: boolean
  /** Success toast after saving — for pages that stay put instead of navigating. */
  successMessage?: string
}

/**
 * Owns the details step: load or parse a profile, edit every extracted section
 * locally, then persist as the complete `details` section via PATCH /profile.
 * Also powers the post-onboarding profile editor via {@link OnboardingProfileOptions}.
 */
export function useOnboardingProfile({
  guardCompleted = true,
  successMessage,
}: OnboardingProfileOptions = {}) {
  const [status, setStatus] = useState<OnboardingStatus>("loading")
  const [redirectTo, setRedirectTo] = useState<string | null>(null)
  const [identity, setIdentity] = useState<Identity>(EMPTY_IDENTITY)
  const [socialLinks, setSocialLinks] = useState<SocialLinksState>(EMPTY_LINKS)
  const [summary, setSummary] = useState("")
  const [technologies, setTechnologies] = useState<string[]>([])
  const [accountEmail, setAccountEmail] = useState("")
  const [sourceResumeId, setSourceResumeId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<ToastData | null>(null)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [loadError, setLoadError] = useState<string | null>(null)
  const [projectConflict, setProjectConflict] = useState<string | null>(null)
  const [reloadingProjects, setReloadingProjects] = useState(false)

  const clearFieldError = useCallback((path: string) => {
    setFieldErrors((prev) => {
      if (!(path in prev)) return prev
      const next = { ...prev }
      delete next[path]
      return next
    })
  }, [])

  const education = useListController<EditableEducation>(
    () => ({
      institution: "",
      degree: "",
      field: "",
      start_date: "",
      end_date: "",
    }),
    "education",
    fieldErrors,
    setFieldErrors,
  )
  const certifications = useListController<EditableCertification>(
    () => ({
      name: "",
      issuer: "",
      issued_at: "",
      expires_at: "",
    }),
    "certifications",
    fieldErrors,
    setFieldErrors,
  )
  const employment = useListController<EditableEmployment>(
    () => ({
      company_name: "",
      title: "",
      start_date: "",
      end_date: "",
      description: "",
    }),
    "employment_history",
    fieldErrors,
    setFieldErrors,
  )
  const projects = useListController<EditableProject>(
    () => ({
      project_id: null,
      name: "",
      summary: "",
      github_url: "",
      deployed_url: "",
      technologies: [],
    }),
    "projects",
    fieldErrors,
    setFieldErrors,
  )

  const hydrate = useCallback(
    (snapshot: OnboardingSnapshot) => {
      const { profile } = snapshot
      setIdentity({
        first_name: profile.first_name ?? "",
        last_name: profile.last_name ?? "",
        phone_number: profile.phone_number ?? "",
        location: profile.location ?? "",
        title: profile.title ?? "",
      })
      setSocialLinks({
        github_url: profile.social_links.github_url ?? "",
        linkedin_url: profile.social_links.linkedin_url ?? "",
        portfolio_url: profile.social_links.portfolio_url ?? "",
      })
      setSummary(profile.summary ?? "")
      setTechnologies([...profile.technologies])
      setAccountEmail(profile.account_email ?? "")
      setSourceResumeId(profile.source_resume_id)
      education.setItems(
        profile.education.map((item) => ({
          institution: item.institution ?? "",
          degree: item.degree ?? "",
          field: item.field ?? "",
          start_date: item.start_date ?? "",
          end_date: item.end_date ?? "",
        })),
      )
      certifications.setItems(
        profile.certifications.map((item) => ({
          name: item.name ?? "",
          issuer: item.issuer ?? "",
          issued_at: item.issued_at ?? "",
          expires_at: item.expires_at ?? "",
        })),
      )
      employment.setItems(
        snapshot.employment_history.map((item) => ({
          company_name: item.company_name,
          title: item.title,
          // API dates are YYYY-MM-DD; month inputs want YYYY-MM.
          start_date: item.start_date?.slice(0, 7) ?? "",
          end_date: item.end_date?.slice(0, 7) ?? "",
          description: item.description ?? "",
        })),
      )
      projects.setItems(editableProjects(snapshot))
      setFieldErrors({})
      setProjectConflict(null)
      setStatus("ready")
    },
    // setItems functions are stable; listing the controllers would loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  // Bumping this re-runs the load effect; retry() (an event handler) triggers it.
  const [reloadNonce, setReloadNonce] = useState(0)

  useEffect(() => {
    let active = true
    void (async () => {
      try {
        const snapshot = await getOnboarding()
        if (!active) return
        if (!snapshot || !snapshot.source_resume) setStatus("empty")
        else if (snapshot.onboarding_complete && guardCompleted) setRedirectTo(COMPLETED_DESTINATION)
        else hydrate(snapshot)
      } catch (error) {
        if (!active) return
        // Never fall back to the dropzone/empty form: uploading without the existing
        // resume id would fork a second resume, and saving would blank stored data.
        setLoadError(messageOf(error))
        setStatus("load_error")
      }
    })()
    return () => {
      active = false
    }
  }, [hydrate, guardCompleted, reloadNonce])

  const retry = useCallback(() => {
    setStatus("loading")
    setLoadError(null)
    setReloadNonce((n) => n + 1)
  }, [])

  const replaceProjects = projects.setItems
  const reloadProjects = useCallback(async (): Promise<boolean> => {
    setReloadingProjects(true)
    try {
      const snapshot = await getOnboarding()
      if (!snapshot) {
        setToast({
          variant: "error",
          message: "Your latest projects could not be loaded. Please try again.",
        })
        return false
      }

      replaceProjects(editableProjects(snapshot))
      setFieldErrors((prev) =>
        Object.fromEntries(
          Object.entries(prev).filter(([path]) => !isProjectErrorPath(path)),
        ),
      )
      setProjectConflict(null)
      setToast({
        variant: "success",
        message: "Latest projects loaded. Review them, then save again.",
      })
      return true
    } catch (error) {
      // Keep both the edited projects and the recovery action available.
      setToast(errorToast(error))
      return false
    } finally {
      setReloadingProjects(false)
    }
  }, [replaceProjects])

  const uploadCv = useCallback(
    async (file: File) => {
      const invalid = validateFile(file)
      if (invalid) {
        setToast({ variant: "error", message: invalid })
        return
      }
      const previous = status
      setStatus("parsing")
      try {
        // Re-uploads replace the source resume in place (no second slot used).
        hydrate(await uploadCvRequest(file, sourceResumeId))
      } catch (error) {
        setStatus(previous === "ready" ? "ready" : "empty")
        setToast(errorToast(error))
      }
    },
    [status, sourceResumeId, hydrate],
  )

  /** Back to the dropzone; the next upload still replaces the source resume. */
  const reupload = useCallback(() => setStatus("empty"), [])

  const setIdentityField = useCallback((key: keyof Identity, value: string) => {
    setIdentity((prev) => ({ ...prev, [key]: value }))
    clearFieldError(key)
  }, [clearFieldError])

  const setSocialLink = useCallback((key: keyof SocialLinksState, value: string) => {
    setSocialLinks((prev) => ({ ...prev, [key]: value }))
    clearFieldError(`social_links.${key}`)
  }, [clearFieldError])

  const setSummaryField = useCallback((value: string) => {
    setSummary(value)
    clearFieldError("summary")
  }, [clearFieldError])

  const addTechnology = useCallback((value: string) => {
    const technology = value.trim()
    if (!technology) return
    setTechnologies((prev) =>
      prev.some((t) => t.toLowerCase() === technology.toLowerCase()) ? prev : [...prev, technology],
    )
    clearFieldError("technologies")
  }, [clearFieldError])

  const removeTechnology = useCallback((value: string) => {
    setTechnologies((prev) => prev.filter((t) => t !== value))
    clearFieldError("technologies")
  }, [clearFieldError])

  /** Mirror of the backend's strict rules for immediate, field-level feedback. */
  const validate = useCallback((): FieldErrors => {
    const errors: FieldErrors = {}
    if (!identity.first_name.trim()) errors.first_name = "Enter your first name."
    if (!identity.last_name.trim()) errors.last_name = "Enter your last name."
    if (!identity.title.trim()) errors.title = "Enter your professional title."

    education.items.forEach((row, index) => {
      if (!hasContent(row)) return
      if (!row.institution.trim())
        errors[`education.${index}.institution`] = "Enter the institution."
      for (const field of ["start_date", "end_date"] as const) {
        const value = row[field].trim()
        if (value && !validYearOrMonth(value))
          errors[`education.${index}.${field}`] =
            "Use YYYY or YYYY-MM, with a year from 1900 to 2100."
      }
      if (unambiguouslyPrecedes(row.start_date, row.end_date))
        errors[`education.${index}.end_date`] =
          "The education end date cannot be before its start date."
    })

    certifications.items.forEach((row, index) => {
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

    employment.items.forEach((row, index) => {
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
      if (
        validMonth(row.start_date) &&
        validMonth(row.end_date) &&
        row.end_date < row.start_date
      )
        errors[`employment_history.${index}.end_date`] =
          "The end month cannot be before the start month."
    })

    projects.items.forEach((row, index) => {
      if (hasContent(row) && !row.name.trim())
        errors[`projects.${index}.name`] = "Enter the project name."
    })
    return errors
  }, [identity, education.items, certifications.items, employment.items, projects.items])

  /**
   * Validate and build the complete details payload, or null after surfacing
   * the inline errors. Split from submitting so the profile editor can send
   * this section together with preferences in one atomic PATCH.
   */
  const prepareSave = useCallback((): PreparedDetails | null => {
    const invalid = validate()
    if (Object.keys(invalid).length) {
      setFieldErrors(invalid)
      setToast({
        variant: "error",
        message: `Fix the ${Object.keys(invalid).length} highlighted ${
          Object.keys(invalid).length === 1 ? "field" : "fields"
        }.`,
      })
      focusFirstError(invalid)
      return null
    }
    setFieldErrors({})
    const projectRows = projects.items
      .map((row, uiIndex) => ({ row, uiIndex }))
      .filter(({ row }) => hasContent(row))
    const payload: ProfileDetailsPayload = {
      first_name: emptyToNull(identity.first_name),
      last_name: emptyToNull(identity.last_name),
      phone_number: emptyToNull(identity.phone_number),
      location: emptyToNull(identity.location),
      title: emptyToNull(identity.title),
      summary: emptyToNull(summary),
      social_links: {
        github_url: emptyToNull(socialLinks.github_url),
        linkedin_url: emptyToNull(socialLinks.linkedin_url),
        portfolio_url: emptyToNull(socialLinks.portfolio_url),
      },
      education: education.items.filter(hasContent).map((row) => ({
        institution: row.institution.trim(),
        degree: emptyToNull(row.degree),
        field: emptyToNull(row.field),
        start_date: row.start_date || null,
        end_date: row.end_date || null,
      })),
      certifications: certifications.items.filter(hasContent).map((row) => ({
        name: row.name.trim(),
        issuer: emptyToNull(row.issuer),
        issued_at: row.issued_at || null,
        expires_at: row.expires_at || null,
      })),
      employment_history: employment.items.filter(hasContent).map((row) => ({
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
      technologies,
    }
    // Blank drafts are filtered out of the payload, so a server error at
    // payload index N has to be mapped back to the row the user can see.
    return { payload, projectPayloadIndexToUiIndex: projectRows.map(({ uiIndex }) => uiIndex) }
  }, [
    validate,
    identity,
    summary,
    socialLinks,
    education.items,
    certifications.items,
    employment.items,
    projects.items,
    technologies,
  ])

  /** Re-seed the form from the saved snapshot (backend-normalized values). */
  const applySnapshot = useCallback(
    (snapshot: OnboardingSnapshot) => {
      hydrate(snapshot)
      if (successMessage) setToast({ variant: "success", message: successMessage })
    },
    [hydrate, successMessage],
  )

  /** Route a failed save onto this section's controls. */
  const applySaveError = useCallback((error: unknown, prepared?: PreparedDetails | null) => {
    if (error instanceof ApiError) {
      const errors = apiFieldErrors(error, prepared?.projectPayloadIndexToUiIndex ?? [])
      setFieldErrors(errors)
      if (error.code === "projects_stale") setProjectConflict(error.message)
      focusFirstError(errors)
    }
    setToast(errorToast(error))
  }, [])

  /** Wizard convenience: prepare, submit this section alone, apply the result. */
  const saveAndContinue = useCallback(async (): Promise<boolean> => {
    const prepared = prepareSave()
    if (!prepared) return false
    setSaving(true)
    try {
      applySnapshot(await updateProfile({ details: prepared.payload }))
      return true
    } catch (error) {
      applySaveError(error, prepared)
      return false
    } finally {
      setSaving(false)
    }
  }, [prepareSave, applySnapshot, applySaveError])

  return {
    status,
    redirectTo,
    loadError,
    retry,
    accountEmail,
    identity,
    setIdentityField,
    socialLinks,
    setSocialLink,
    summary,
    setSummary: setSummaryField,
    technologies,
    addTechnology,
    removeTechnology,
    education,
    certifications,
    employment,
    projects,
    projectConflict,
    reloadingProjects,
    reloadProjects,
    fieldErrors,
    fieldError: (path: string) => fieldErrors[path],
    uploadCv,
    reupload,
    saving,
    toast,
    dismissToast: useCallback(() => setToast(null), []),
    prepareSave,
    applySnapshot,
    applySaveError,
    saveAndContinue,
  }
}

export type OnboardingProfileState = ReturnType<typeof useOnboardingProfile>
