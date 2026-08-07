"use client"

import { useCallback, useEffect, useState } from "react"

import { ApiError } from "@/lib/api/client"
import { apiFieldErrors } from "@/lib/api/fieldErrors"
import { getOnboarding, updateProfile, uploadCv as uploadCvRequest } from "@/lib/api/profile"
import type { OnboardingSnapshot } from "@/lib/api/types"
import {
  projectsFromSnapshot,
  remapProjectRow,
  type PreparedDetails,
} from "@/lib/onboarding/profileDraft"
import { COMPLETED_DESTINATION } from "@/lib/onboarding/routing"
import { useProfileDraft } from "./useProfileDraft"
import type { ToastData } from "@/components/onboarding/Toast"

export type OnboardingStatus = "loading" | "empty" | "parsing" | "ready" | "load_error"

export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024
const ALLOWED_EXTENSIONS = [".pdf", ".docx"]

/**
 * null when the file is acceptable; otherwise the user-facing reason. Type is
 * checked before size, so an unsupported file is named as such however large.
 */
function validateResumeFile(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext)))
    return "That needs to be a PDF or DOCX."
  if (file.size > MAX_UPLOAD_BYTES) return "That file's over 5MB. Try a smaller PDF or DOCX."
  return null
}

const messageOf = (error: unknown): string =>
  error instanceof ApiError ? error.message : "Something went wrong. Try again."

/** An error toast that also surfaces the support reference on a 500. */
const errorToast = (error: unknown): ToastData => ({
  variant: "error",
  message: messageOf(error),
  requestId: error instanceof ApiError ? error.requestId : undefined,
})

export interface OnboardingProfileOptions {
  /** Redirect completed users away (wizard behavior). Pass false on the edit page. */
  guardCompleted?: boolean
  /** Success toast after saving — for pages that stay put instead of navigating. */
  successMessage?: string
  /**
   * Where the snapshot comes from. The profile editor passes a shared loader so
   * mounting this alongside the preferences hook costs one request, not two.
   * `reloadProjects` always refetches directly — it exists to get fresh rows.
   */
  loadSnapshot?: () => Promise<OnboardingSnapshot | null>
}

/**
 * Owns the details step: load or parse a profile, edit every extracted section
 * locally, then persist as the complete `details` section via PATCH /profile.
 * Also powers the post-onboarding profile editor via {@link OnboardingProfileOptions}.
 */
export function useOnboardingProfile({
  guardCompleted = true,
  successMessage,
  loadSnapshot = getOnboarding,
}: OnboardingProfileOptions = {}) {
  const [status, setStatus] = useState<OnboardingStatus>("loading")
  const [redirectTo, setRedirectTo] = useState<string | null>(null)
  const [accountEmail, setAccountEmail] = useState("")
  const [sourceResumeId, setSourceResumeId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<ToastData | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [projectConflict, setProjectConflict] = useState<string | null>(null)
  const [reloadingProjects, setReloadingProjects] = useState(false)

  const onInvalid = useCallback((fieldCount: number) => {
    setToast({
      variant: "error",
      message: `Fix the ${fieldCount} highlighted ${fieldCount === 1 ? "field" : "fields"}.`,
    })
  }, [])
  const draft = useProfileDraft({ onInvalid })
  const { replaceFromSnapshot, replaceProjects, applyServerErrors, prepareSave } = draft

  const hydrate = useCallback(
    (snapshot: OnboardingSnapshot) => {
      replaceFromSnapshot(snapshot)
      // Read-only / upload plumbing, deliberately outside ProfileDraft.
      setAccountEmail(snapshot.profile.account_email ?? "")
      setSourceResumeId(snapshot.profile.source_resume_id)
      setProjectConflict(null)
      setStatus("ready")
    },
    [replaceFromSnapshot],
  )

  // Bumping this re-runs the load effect; retry() (an event handler) triggers it.
  const [reloadNonce, setReloadNonce] = useState(0)

  useEffect(() => {
    let active = true
    void (async () => {
      try {
        const snapshot = await loadSnapshot()
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
  }, [hydrate, guardCompleted, reloadNonce, loadSnapshot])

  const retry = useCallback(() => {
    setStatus("loading")
    setLoadError(null)
    setReloadNonce((n) => n + 1)
  }, [])

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

      replaceProjects(projectsFromSnapshot(snapshot))
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
      const invalid = validateResumeFile(file)
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

  /** Re-seed the form from the saved snapshot (backend-normalized values). */
  const applySnapshot = useCallback(
    (snapshot: OnboardingSnapshot) => {
      hydrate(snapshot)
      if (successMessage) setToast({ variant: "success", message: successMessage })
    },
    [hydrate, successMessage],
  )

  /** Route a failed save onto this section's controls. */
  const applySaveError = useCallback(
    (error: unknown, prepared?: PreparedDetails | null) => {
      if (error instanceof ApiError) {
        applyServerErrors(
          apiFieldErrors(error, {
            section: "details",
            remapPath: remapProjectRow(prepared?.projectPayloadIndexToUiIndex ?? []),
          }),
        )
        if (error.code === "projects_stale") setProjectConflict(error.message)
      }
      setToast(errorToast(error))
    },
    [applyServerErrors],
  )

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
    identity: draft.identity,
    setIdentityField: draft.setIdentityField,
    socialLinks: draft.socialLinks,
    setSocialLink: draft.setSocialLink,
    summary: draft.summary,
    setSummary: draft.setSummary,
    technologies: draft.technologies,
    addTechnology: draft.addTechnology,
    removeTechnology: draft.removeTechnology,
    education: draft.education,
    certifications: draft.certifications,
    employment: draft.employment,
    projects: draft.projects,
    projectConflict,
    reloadingProjects,
    reloadProjects,
    fieldErrors: draft.fieldErrors,
    fieldError: draft.fieldError,
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