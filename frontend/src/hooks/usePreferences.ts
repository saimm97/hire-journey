"use client"

import { useCallback, useEffect, useState } from "react"

import { ApiError } from "@/lib/api/client"
import { profileApi } from "@/lib/api/profile"
import type { Toast } from "@/hooks/useProfileOnboarding"

export type PreferencesStatus = "loading" | "ready"

export type WorkMode = "remote" | "hybrid" | "onsite"

const messageOf = (error: unknown): string =>
  error instanceof ApiError ? error.message : "Something went wrong. Try again."

/** Case-insensitive unique append; mirrors the skills editor's de-dup rule. */
const addUnique = (list: string[], value: string): string[] => {
  const next = value.trim()
  if (!next) return list
  return list.some((item) => item.toLowerCase() === next.toLowerCase()) ? list : [...list, next]
}

/**
 * Owns the preferences step: load the persisted job preferences (roles, salary,
 * locations, work mode, "open to relocating"), edit everything locally, then
 * persist. All backend access goes through `profileApi`, keeping the page and
 * components presentational.
 */
export function usePreferences() {
  const [status, setStatus] = useState<PreferencesStatus>("loading")
  const [roles, setRoles] = useState<string[]>([])
  const [seniority, setSeniority] = useState<string[]>([])
  const [minimumSalary, setMinimumSalary] = useState<number | null>(null)
  const [locations, setLocations] = useState<string[]>([])
  const [openToRelocating, setOpenToRelocating] = useState(false)
  const [workMode, setWorkMode] = useState<WorkMode | null>(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)

  useEffect(() => {
    let active = true
    profileApi
      .get()
      .then((snapshot) => {
        if (!active) return
        if (snapshot) {
          const { profile } = snapshot
          setRoles(profile.desired_role ?? [])
          setSeniority(profile.seniority_level ?? [])
          setMinimumSalary(profile.minimum_salary)
          setLocations(profile.location ?? [])
          setWorkMode(profile.work_mode as WorkMode | null)
          setOpenToRelocating(profile.open_to_relocating)
        }
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
  }, [])

  const addRole = useCallback((value: string) => setRoles((prev) => addUnique(prev, value)), [])
  const removeRole = useCallback(
    (role: string) => setRoles((prev) => prev.filter((r) => r !== role)),
    [],
  )

  const addSeniority = useCallback(
    (value: string) => setSeniority((prev) => addUnique(prev, value)),
    [],
  )
  const removeSeniority = useCallback(
    (level: string) => setSeniority((prev) => prev.filter((l) => l !== level)),
    [],
  )

  const addLocation = useCallback(
    (value: string) => setLocations((prev) => addUnique(prev, value)),
    [],
  )
  const removeLocation = useCallback(
    (location: string) => setLocations((prev) => prev.filter((l) => l !== location)),
    [],
  )

  const save = useCallback(async (): Promise<boolean> => {
    setSaving(true)
    try {
      await profileApi.update({
        desired_role: roles,
        seniority_level: seniority,
        minimum_salary: minimumSalary,
        location: locations,
        work_mode: workMode,
        open_to_relocating: openToRelocating,
      })
      setToast({ variant: "success", message: "Preferences saved. Time to find your matches." })
      return true
    } catch (error) {
      setToast({ variant: "error", message: messageOf(error) })
      return false
    } finally {
      setSaving(false)
    }
  }, [roles, seniority, minimumSalary, locations, workMode, openToRelocating])

  return {
    status,
    roles,
    seniority,
    minimumSalary,
    locations,
    openToRelocating,
    workMode,
    saving,
    toast,
    addRole,
    removeRole,
    addSeniority,
    removeSeniority,
    setMinimumSalary,
    addLocation,
    removeLocation,
    setOpenToRelocating,
    setWorkMode,
    save,
    dismissToast: useCallback(() => setToast(null), []),
  }
}
