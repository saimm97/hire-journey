"use client"

import { useCallback, useEffect, useState } from "react"

import { ApiError } from "@/lib/api/client"
import { apiFieldErrors, groupError as matchGroupError, type FieldErrors } from "@/lib/api/fieldErrors"
import { getOnboarding, updateProfile } from "@/lib/api/profile"
import type {
  OnboardingSnapshot,
  PreferencesPayload,
  SeniorityLevel,
  WorkMode,
} from "@/lib/api/types"
import { SENIORITY_LEVELS, WORK_MODES } from "@/lib/api/types"
import { COMPLETED_DESTINATION } from "@/lib/onboarding/routing"
import type { ToastData } from "@/components/onboarding/Toast"

export type PreferencesStatus = "loading" | "ready" | "load_error"

const messageOf = (error: unknown): string =>
  error instanceof ApiError ? error.message : "Something went wrong. Try again."

/** An error toast that also surfaces the support reference on a 500. */
const errorToast = (error: unknown): ToastData => ({
  variant: "error",
  message: messageOf(error),
  requestId: error instanceof ApiError ? error.requestId : undefined,
})

const addUnique = (values: string[], value: string): string[] => {
  const trimmed = value.trim()
  if (!trimmed) return values
  return values.some((v) => v.toLowerCase() === trimmed.toLowerCase())
    ? values
    : [...values, trimmed]
}

export interface PreferencesOptions {
  /** Redirect completed users away (wizard behavior). Pass false on the edit page. */
  guardCompleted?: boolean
  /** Success toast after saving — for pages that stay put instead of navigating. */
  successMessage?: string
}

/**
 * Owns the preferences step: hydrate from the snapshot, edit locally, persist
 * as the complete `preferences` section via PATCH /profile. Redirect decisions
 * surface as `redirectTo`.
 */
export function usePreferences({
  guardCompleted = true,
  successMessage,
}: PreferencesOptions = {}) {
  const [status, setStatus] = useState<PreferencesStatus>("loading")
  const [redirectTo, setRedirectTo] = useState<string | null>(null)
  const [roles, setRoles] = useState<string[]>([])
  const [locations, setLocations] = useState<string[]>([])
  const [workModes, setWorkModes] = useState<WorkMode[]>([])
  const [seniority, setSeniority] = useState<SeniorityLevel | null>(null)
  const [minimumSalary, setMinimumSalary] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<ToastData | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})

  const clearFieldError = useCallback((key: string) => {
    setFieldErrors((prev) => {
      if (!(key in prev)) return prev
      const next = { ...prev }
      delete next[key]
      return next
    })
  }, [])

  /** Mirror of the backend's required-field rules for immediate feedback. */
  const validate = useCallback((): FieldErrors => {
    const errors: FieldErrors = {}
    if (!roles.length) errors.desired_roles = "Add at least one desired role."
    if (!locations.length)
      errors.desired_locations = "Add at least one desired location."
    if (!workModes.length) errors.work_modes_preferred = "Pick at least one work mode."
    if (!seniority) errors.seniority_level = "Pick your seniority level."
    return errors
  }, [roles, locations, workModes, seniority])

  /** Seed the controls from a snapshot — used on load and after a save. */
  const hydrate = useCallback((snapshot: OnboardingSnapshot) => {
    const { profile } = snapshot
    setRoles(profile.desired_roles)
    setLocations(profile.desired_locations)
    setWorkModes(
      profile.work_modes_preferred.filter((m): m is WorkMode =>
        (WORK_MODES as string[]).includes(m),
      ),
    )
    setSeniority(
      (SENIORITY_LEVELS as string[]).includes(profile.seniority_level ?? "")
        ? (profile.seniority_level as SeniorityLevel)
        : null,
    )
    setMinimumSalary(profile.minimum_salary)
    setFieldErrors({})
  }, [])

  // Bumping this re-runs the load effect; retry() (an event handler) triggers it.
  const [reloadNonce, setReloadNonce] = useState(0)

  useEffect(() => {
    let active = true
    void (async () => {
      try {
        const snapshot = await getOnboarding()
        if (!active) return
        // Deep link without a resume -> back to the profile step; done -> app.
        if (!snapshot || !snapshot.source_resume) {
          setRedirectTo("/onboarding/profile")
          return
        }
        if ((snapshot.completion_issues ?? []).some((issue) => issue.step === "profile")) {
          setRedirectTo("/onboarding/profile")
          return
        }
        if (snapshot.onboarding_complete && guardCompleted) {
          setRedirectTo(COMPLETED_DESTINATION)
          return
        }
        hydrate(snapshot)
        setStatus("ready")
      } catch (error) {
        if (!active) return
        // Never render an empty editable form on a failed load: saving it would
        // wipe stored salary/locations. Show a retry instead.
        setLoadError(messageOf(error))
        setStatus("load_error")
      }
    })()
    return () => {
      active = false
    }
  }, [guardCompleted, reloadNonce, hydrate])

  const retry = useCallback(() => {
    setStatus("loading")
    setLoadError(null)
    setReloadNonce((n) => n + 1)
  }, [])

  const toggleWorkMode = useCallback(
    (mode: WorkMode) => {
      setWorkModes((prev) =>
        prev.includes(mode) ? prev.filter((m) => m !== mode) : [...prev, mode],
      )
      clearFieldError("work_modes_preferred")
    },
    [clearFieldError],
  )

  const selectSeniority = useCallback(
    (value: SeniorityLevel | null) => {
      setSeniority(value)
      clearFieldError("seniority_level")
    },
    [clearFieldError],
  )

  const changeSalary = useCallback(
    (value: number | null) => {
      setMinimumSalary(value)
      clearFieldError("minimum_salary")
    },
    [clearFieldError],
  )

  /**
   * Validate and build the complete preferences payload, or null after
   * surfacing the inline errors. Split from submitting so the profile editor
   * can send this section together with details in one atomic PATCH.
   */
  const prepareSave = useCallback((): PreferencesPayload | null => {
    const invalid = validate()
    if (Object.keys(invalid).length) {
      setFieldErrors(invalid)
      const count = Object.keys(invalid).length
      setToast({
        variant: "error",
        message: `Fix the ${count} highlighted ${count === 1 ? "field" : "fields"}.`,
      })
      return null
    }
    setFieldErrors({})
    return {
      minimum_salary: minimumSalary,
      desired_roles: roles,
      desired_locations: locations,
      work_modes_preferred: workModes,
      seniority_level: seniority as SeniorityLevel,
    }
  }, [validate, roles, locations, workModes, seniority, minimumSalary])

  /** Re-seed the controls from the saved snapshot (backend-normalized values). */
  const applySnapshot = useCallback(
    (snapshot: OnboardingSnapshot) => {
      hydrate(snapshot)
      if (successMessage) setToast({ variant: "success", message: successMessage })
    },
    [hydrate, successMessage],
  )

  /** Route a failed save onto this section's controls. */
  const applySaveError = useCallback((error: unknown) => {
    // Server-side field errors (e.g. an empty list slipped past the client)
    // land on the exact section instead of a bare toast.
    if (error instanceof ApiError && error.fields.length) {
      setFieldErrors(apiFieldErrors(error, "preferences"))
    }
    setToast(errorToast(error))
  }, [])

  /** Wizard convenience: prepare, submit this section alone, apply the result. */
  const save = useCallback(async (): Promise<boolean> => {
    const payload = prepareSave()
    if (!payload) return false
    setSaving(true)
    try {
      const snapshot = await updateProfile({ preferences: payload })
      // The wizard's last step must not "finish" an incomplete profile.
      if (!snapshot.onboarding_complete) {
        const missingProfile = (snapshot.completion_issues ?? []).filter(
          (issue) => issue.step === "profile",
        )
        setToast({
          variant: "error",
          message: missingProfile.length
            ? `Finish your profile first: ${missingProfile
                .map((issue) => issue.message)
                .join(" ")}`
            : "Some onboarding requirements are still incomplete. Review your details and try again.",
        })
        return false
      }
      applySnapshot(snapshot)
      return true
    } catch (error) {
      applySaveError(error)
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
    roles,
    addRole: useCallback(
      (value: string) => {
        setRoles((prev) => addUnique(prev, value))
        clearFieldError("desired_roles")
      },
      [clearFieldError],
    ),
    removeRole: useCallback(
      (value: string) => setRoles((prev) => prev.filter((v) => v !== value)),
      [],
    ),
    locations,
    addLocation: useCallback(
      (value: string) => {
        setLocations((prev) => addUnique(prev, value))
        clearFieldError("desired_locations")
      },
      [clearFieldError],
    ),
    removeLocation: useCallback(
      (value: string) => setLocations((prev) => prev.filter((v) => v !== value)),
      [],
    ),
    workModes,
    toggleWorkMode,
    seniority,
    setSeniority: selectSeniority,
    minimumSalary,
    setMinimumSalary: changeSalary,
    saving,
    toast,
    dismissToast: useCallback(() => setToast(null), []),
    fieldErrors,
    fieldError: (path: string) => fieldErrors[path],
    groupError: (prefix: string) => matchGroupError(fieldErrors, prefix),
    prepareSave,
    applySnapshot,
    applySaveError,
    save,
  }
}

export type PreferencesState = ReturnType<typeof usePreferences>
