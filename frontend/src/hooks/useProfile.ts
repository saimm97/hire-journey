"use client"

import { useProfileResource } from "@/lib/profile/ProfileContext"

/**
 * Read the shared profile cache. Returns the flattened profile alongside the
 * full snapshot; `refresh()` re-pulls after an edit so every consumer updates.
 */
export function useProfile() {
  const { data, loading, error, refresh } = useProfileResource()
  return {
    snapshot: data,
    profile: data?.profile ?? null,
    loading,
    error,
    refresh,
  }
}
