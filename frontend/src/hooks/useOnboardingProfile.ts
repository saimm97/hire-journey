"use client"

import { useCallback, useEffect, useState } from "react"

import { ApiError } from "@/lib/api/client"
import { getOnboarding, saveDetails, uploadCv as uploadCvRequest } from "@/lib/api/profile"
import type { OnboardingSnapshot, ProfileDetailsPayload } from "@/lib/api/types"
import { COMPLETED_DESTINATION } from "@/lib/onboarding/routing"
import type { ToastData } from "@/components/onboarding/Toast"

export type OnboardingStatus = "loading" | "empty" | "parsing" | "ready"

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
}

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

const emptyToNull = (value: string): string | null => value.trim() || null

const messageOf = (error: unknown): string =>
  error instanceof ApiError ? error.message : "Something went wrong. Try again."

/** True when the user typed anything into the row (empty rows are dropped silently). */
const hasContent = (row: object): boolean =>
  Object.values(row).some((value: unknown) =>
    typeof value === "string" ? value.trim() : Array.isArray(value) ? value.length : false,
  )

function validateFile(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext)))
    return "That needs to be a PDF or DOCX."
  if (file.size > MAX_UPLOAD_BYTES) return "That file's over 5MB. Try a smaller PDF or DOCX."
  return null
}

/** Local list state with the add/update/remove surface every repeatable editor needs. */
function useListController<T>(makeEmpty: () => T): ListController<T> & {
  setItems: (items: T[]) => void
} {
  const [items, setItems] = useState<T[]>([])
  return {
    items,
    setItems,
    add: useCallback(() => setItems((prev) => [...prev, makeEmpty()]), [makeEmpty]),
    update: useCallback(
      (index: number, patch: Partial<T>) =>
        setItems((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item))),
      [],
    ),
    remove: useCallback(
      (index: number) => setItems((prev) => prev.filter((_, i) => i !== index)),
      [],
    ),
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
 * locally, then persist via PUT /profile/details. Pages stay presentational.
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

  const education = useListController<EditableEducation>(() => ({
    institution: "",
    degree: "",
    field: "",
    start_date: "",
    end_date: "",
  }))
  const certifications = useListController<EditableCertification>(() => ({
    name: "",
    issuer: "",
    issued_at: "",
    expires_at: "",
  }))
  const employment = useListController<EditableEmployment>(() => ({
    company_name: "",
    title: "",
    start_date: "",
    end_date: "",
    description: "",
  }))
  const projects = useListController<EditableProject>(() => ({
    project_id: null,
    name: "",
    summary: "",
    github_url: "",
    deployed_url: "",
    technologies: [],
  }))

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
      projects.setItems(
        snapshot.projects.map((project) => ({
          project_id: project.project_id,
          name: project.name,
          summary: project.summary ?? "",
          github_url: project.github_url ?? "",
          deployed_url: project.deployed_url ?? "",
          technologies: [...project.tech_stack],
        })),
      )
      setStatus("ready")
    },
    // setItems functions are stable; listing the controllers would loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  useEffect(() => {
    let active = true
    getOnboarding()
      .then((snapshot) => {
        if (!active) return
        if (!snapshot || !snapshot.source_resume) setStatus("empty")
        else if (snapshot.onboarding_complete && guardCompleted)
          setRedirectTo(COMPLETED_DESTINATION)
        else hydrate(snapshot)
      })
      .catch((error) => {
        if (!active) return
        setStatus("empty")
        setToast({ variant: "error", message: messageOf(error) })
      })
    return () => {
      active = false
    }
  }, [hydrate, guardCompleted])

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
        setToast({ variant: "error", message: messageOf(error) })
      }
    },
    [status, sourceResumeId, hydrate],
  )

  /** Back to the dropzone; the next upload still replaces the source resume. */
  const reupload = useCallback(() => setStatus("empty"), [])

  const setIdentityField = useCallback((key: keyof Identity, value: string) => {
    setIdentity((prev) => ({ ...prev, [key]: value }))
  }, [])

  const setSocialLink = useCallback((key: keyof SocialLinksState, value: string) => {
    setSocialLinks((prev) => ({ ...prev, [key]: value }))
  }, [])

  const addTechnology = useCallback((value: string) => {
    const technology = value.trim()
    if (!technology) return
    setTechnologies((prev) =>
      prev.some((t) => t.toLowerCase() === technology.toLowerCase()) ? prev : [...prev, technology],
    )
  }, [])

  const removeTechnology = useCallback((value: string) => {
    setTechnologies((prev) => prev.filter((t) => t !== value))
  }, [])

  /** Mirror of the backend's strict rules; returns an error message or null. */
  const validate = useCallback((): string | null => {
    for (const row of education.items.filter(hasContent))
      if (!row.institution.trim()) return "Each education entry needs an institution."
    for (const row of certifications.items.filter(hasContent))
      if (!row.name.trim()) return "Each certification needs a name."
    for (const row of employment.items.filter(hasContent)) {
      if (!row.company_name.trim() || !row.title.trim())
        return "Each employment entry needs a company and a title."
      if (row.start_date && row.end_date && row.end_date < row.start_date)
        return "An employment end date cannot be before its start date."
    }
    for (const row of projects.items.filter(hasContent))
      if (!row.name.trim()) return "Each project needs a name."
    return null
  }, [education.items, certifications.items, employment.items, projects.items])

  const saveAndContinue = useCallback(async (): Promise<boolean> => {
    const invalid = validate()
    if (invalid) {
      setToast({ variant: "error", message: invalid })
      return false
    }
    setSaving(true)
    try {
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
        projects: projects.items.filter(hasContent).map((row) => ({
          project_id: row.project_id,
          name: row.name.trim(),
          summary: emptyToNull(row.summary),
          github_url: emptyToNull(row.github_url),
          deployed_url: emptyToNull(row.deployed_url),
          technologies: row.technologies,
        })),
        technologies,
      }
      hydrate(await saveDetails(payload))
      if (successMessage) setToast({ variant: "success", message: successMessage })
      return true
    } catch (error) {
      setToast({ variant: "error", message: messageOf(error) })
      return false
    } finally {
      setSaving(false)
    }
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
    hydrate,
    successMessage,
  ])

  return {
    status,
    redirectTo,
    accountEmail,
    identity,
    setIdentityField,
    socialLinks,
    setSocialLink,
    summary,
    setSummary,
    technologies,
    addTechnology,
    removeTechnology,
    education,
    certifications,
    employment,
    projects,
    uploadCv,
    reupload,
    saving,
    toast,
    dismissToast: useCallback(() => setToast(null), []),
    saveAndContinue,
  }
}

export type OnboardingProfileState = ReturnType<typeof useOnboardingProfile>
