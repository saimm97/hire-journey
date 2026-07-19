"use client"

import { useCallback, useEffect, useState } from "react"

import { ApiError } from "@/lib/api/client"
import { getOnboarding, savePreferences } from "@/lib/api/profile"
import type { SeniorityLevel, WorkMode } from "@/lib/api/types"
import { SENIORITY_LEVELS, WORK_MODES } from "@/lib/api/types"
import { COMPLETED_DESTINATION } from "@/lib/onboarding/routing"
import type { ToastData } from "@/components/onboarding/Toast"

export type PreferencesStatus = "loading" | "ready"

const messageOf = (error: unknown): string =>
  error instanceof ApiError ? error.message : "Something went wrong. Try again."

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
 * via PUT /profile/preferences. Redirect decisions surface as `redirectTo`.
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

  useEffect(() => {
    let active = true
    getOnboarding()
      .then((snapshot) => {
        if (!active) return
        // Deep link without a resume -> back to the profile step; done -> app.
        if (!snapshot || !snapshot.source_resume) {
          setRedirectTo("/onboarding/profile")
          return
        }
        if (snapshot.onboarding_complete && guardCompleted) {
          setRedirectTo(COMPLETED_DESTINATION)
          return
        }
        const { profile } = snapshot
        setRoles(profile.desired_roles)
        setLocations(profile.desired_locations)
        setWorkModes(profile.work_modes_preferred.filter((m): m is WorkMode =>
          (WORK_MODES as string[]).includes(m),
        ))
        setSeniority(
          (SENIORITY_LEVELS as string[]).includes(profile.seniority_level ?? "")
            ? (profile.seniority_level as SeniorityLevel)
            : null,
        )
        setMinimumSalary(profile.minimum_salary)
        setStatus("ready")
      })
      .catch((error) => {
        if (!active) return
        setStatus("ready")
        setToast({ variant: "error", message: messageOf(error) })
      })
    return () => {
      active = false
    }
  }, [guardCompleted])

  const toggleWorkMode = useCallback((mode: WorkMode) => {
    setWorkModes((prev) =>
      prev.includes(mode) ? prev.filter((m) => m !== mode) : [...prev, mode],
    )
  }, [])

  const save = useCallback(async (): Promise<boolean> => {
    if (!roles.length) {
      setToast({ variant: "error", message: "Add at least one desired role." })
      return false
    }
    if (!workModes.length) {
      setToast({ variant: "error", message: "Pick at least one work mode." })
      return false
    }
    if (!seniority) {
      setToast({ variant: "error", message: "Pick your seniority level." })
      return false
    }
    setSaving(true)
    try {
      const snapshot = await savePreferences({
        minimum_salary: minimumSalary,
        desired_roles: roles,
        desired_locations: locations,
        work_modes_preferred: workModes,
        seniority_level: seniority,
      })
      if (!snapshot.onboarding_complete) {
        setToast({
          variant: "error",
          message: "Almost there — finish your profile details first.",
        })
        return false
      }
      if (successMessage) setToast({ variant: "success", message: successMessage })
      return true
    } catch (error) {
      setToast({ variant: "error", message: messageOf(error) })
      return false
    } finally {
      setSaving(false)
    }
  }, [roles, locations, workModes, seniority, minimumSalary, successMessage])

  return {
    status,
    redirectTo,
    roles,
    addRole: useCallback((value: string) => setRoles((prev) => addUnique(prev, value)), []),
    removeRole: useCallback(
      (value: string) => setRoles((prev) => prev.filter((v) => v !== value)),
      [],
    ),
    locations,
    addLocation: useCallback(
      (value: string) => setLocations((prev) => addUnique(prev, value)),
      [],
    ),
    removeLocation: useCallback(
      (value: string) => setLocations((prev) => prev.filter((v) => v !== value)),
      [],
    ),
    workModes,
    toggleWorkMode,
    seniority,
    setSeniority,
    minimumSalary,
    setMinimumSalary,
    saving,
    toast,
    dismissToast: useCallback(() => setToast(null), []),
    save,
  }
}

export type PreferencesState = ReturnType<typeof usePreferences>
