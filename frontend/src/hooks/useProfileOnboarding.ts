"use client"

import { useCallback, useEffect, useState } from "react"

import { ApiError } from "@/lib/api/client"
import { profileApi } from "@/lib/api/profile"
import type { ProfileSnapshot, Project, ProjectInput } from "@/lib/api/types"

export type OnboardingStatus = "loading" | "empty" | "parsing" | "ready"

export interface Identity {
  first_name: string
  last_name: string
  email: string
  phone: string
  github_url: string
  portfolio_url: string
}

export interface Toast {
  variant: "error" | "success"
  message: string
}

const EMPTY_IDENTITY: Identity = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  github_url: "",
  portfolio_url: "",
}

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024
const ALLOWED_EXTENSIONS = [".pdf", ".docx"]

const emptyToNull = (value: string): string | null => value.trim() || null

const toProjectInput = (project: Project): ProjectInput => ({
  name: project.name,
  summary: project.summary,
  tech_stack: project.tech_stack ?? [],
  github_url: project.github_url,
  deployed_url: project.deployed_url,
  source: project.source,
})

const PROJECTS_PDF_SOURCE = "projects_pdf"

const messageOf = (error: unknown): string =>
  error instanceof ApiError ? error.message : "Something went wrong. Try again."

function validateFile(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))) return "That needs to be a PDF or DOCX."
  if (file.size > MAX_UPLOAD_BYTES) return "That file's over 5MB. Try a smaller PDF or DOCX."
  return null
}

/**
 * Owns the onboarding flow: load or parse a profile, edit the fields locally,
 * then persist. All backend access goes through `profileApi`; the page and the
 * components stay presentational.
 */
export function useProfileOnboarding() {
  const [status, setStatus] = useState<OnboardingStatus>("loading")
  const [identity, setIdentity] = useState<Identity>(EMPTY_IDENTITY)
  const [skills, setSkills] = useState<string[]>([])
  const [summary, setSummary] = useState<string | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [saving, setSaving] = useState(false)
  const [parsingProjects, setParsingProjects] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)

  const hydrate = useCallback((snapshot: ProfileSnapshot) => {
    const { profile } = snapshot
    setIdentity({
      first_name: profile.first_name ?? "",
      last_name: profile.last_name ?? "",
      email: profile.email ?? "",
      phone: profile.phone ?? "",
      github_url: profile.github_url ?? "",
      portfolio_url: profile.portfolio_url ?? "",
    })
    setSkills(profile.tech_stack ?? [])
    setSummary(snapshot.resume_summary)
    setProjects(snapshot.projects)
    setStatus("ready")
  }, [])

  useEffect(() => {
    let active = true
    profileApi
      .get()
      .then((snapshot) => {
        if (!active) return
        if (snapshot) hydrate(snapshot)
        else setStatus("empty")
      })
      .catch((error) => {
        if (!active) return
        setStatus("empty")
        setToast({ variant: "error", message: messageOf(error) })
      })
    return () => {
      active = false
    }
  }, [hydrate])

  const uploadCv = useCallback(
    async (file: File) => {
      const invalid = validateFile(file)
      if (invalid) {
        setToast({ variant: "error", message: invalid })
        return
      }
      setStatus("parsing")
      try {
        hydrate(await profileApi.uploadCv(file))
      } catch (error) {
        setStatus("empty")
        setToast({ variant: "error", message: messageOf(error) })
      }
    },
    [hydrate],
  )

  const uploadProjects = useCallback(async (file: File) => {
    const invalid = validateFile(file)
    if (invalid) {
      setToast({ variant: "error", message: invalid })
      return
    }
    setParsingProjects(true)
    try {
      const parsed = await profileApi.uploadProjects(file)
      setProjects((prev) => [
        ...prev.filter((p) => p.source !== PROJECTS_PDF_SOURCE),
        ...parsed,
      ])
      setToast({
        variant: "success",
        message: parsed.length
          ? `Added ${parsed.length} project${parsed.length === 1 ? "" : "s"} from your PDF.`
          : "No projects found in that PDF.",
      })
    } catch (error) {
      setToast({ variant: "error", message: messageOf(error) })
    } finally {
      setParsingProjects(false)
    }
  }, [])

  const setIdentityField = useCallback((key: keyof Identity, value: string) => {
    setIdentity((prev) => ({ ...prev, [key]: value }))
  }, [])

  const addSkill = useCallback((value: string) => {
    const skill = value.trim()
    if (!skill) return
    setSkills((prev) =>
      prev.some((s) => s.toLowerCase() === skill.toLowerCase()) ? prev : [...prev, skill],
    )
  }, [])

  const removeSkill = useCallback((skill: string) => {
    setSkills((prev) => prev.filter((s) => s !== skill))
  }, [])

  const removeProject = useCallback((projectId: string) => {
    setProjects((prev) => prev.filter((p) => p.project_id !== projectId))
  }, [])

  const updateProject = useCallback((projectId: string, patch: Partial<Project>) => {
    setProjects((prev) => prev.map((p) => (p.project_id === projectId ? { ...p, ...patch } : p)))
  }, [])

  const setSummaryText = useCallback((value: string) => setSummary(value), [])

  const reupload = useCallback(() => {
    setStatus("empty")
    setIdentity(EMPTY_IDENTITY)
    setSkills([])
    setSummary(null)
    setProjects([])
  }, [])

  const saveAndContinue = useCallback(async (): Promise<boolean> => {
    setSaving(true)
    try {
      await profileApi.update({
        first_name: emptyToNull(identity.first_name),
        last_name: emptyToNull(identity.last_name),
        email: emptyToNull(identity.email),
        phone: emptyToNull(identity.phone),
        github_url: emptyToNull(identity.github_url),
        portfolio_url: emptyToNull(identity.portfolio_url),
        summary: emptyToNull(summary ?? ""),
        tech_stack: skills,
      })
      await profileApi.replaceProjects(projects.map(toProjectInput))
      setToast({ variant: "success", message: "Profile saved. Preferences are up next." })
      return true
    } catch (error) {
      setToast({ variant: "error", message: messageOf(error) })
      return false
    } finally {
      setSaving(false)
    }
  }, [identity, summary, skills, projects])

  return {
    status,
    identity,
    skills,
    summary,
    projects,
    saving,
    parsingProjects,
    toast,
    setIdentityField,
    setSummaryText,
    addSkill,
    removeSkill,
    removeProject,
    updateProject,
    uploadCv,
    uploadProjects,
    reupload,
    saveAndContinue,
    dismissToast: useCallback(() => setToast(null), []),
  }
}
