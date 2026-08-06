"use client"

import { useCallback, useRef, useState } from "react"

import { getOnboarding, updateProfile } from "@/lib/api/profile"
import type { OnboardingSnapshot } from "@/lib/api/types"
import { useOnboardingProfile } from "./useOnboardingProfile"
import { usePreferences } from "./usePreferences"

/**
 * The post-onboarding profile editor: both sections at once.
 *
 * Owns the two things neither section hook can own alone — a single snapshot
 * read shared between them, and a single atomic PATCH carrying both sections.
 * Sending two requests would be two backend transactions, so a failure on the
 * second would leave the first committed.
 */
export function useProfileEditor() {
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loadNonce, setLoadNonce] = useState(0)
  const cache = useRef<{ nonce: number; snapshot: Promise<OnboardingSnapshot | null> } | null>(
    null,
  )

  // Both hooks hydrate from the same snapshot, so one request serves both.
  // Keyed on a nonce so retrying genuinely refetches instead of replaying.
  const loadSnapshot = useCallback(() => {
    if (cache.current?.nonce !== loadNonce) {
      cache.current = { nonce: loadNonce, snapshot: getOnboarding() }
    }
    return cache.current.snapshot
  }, [loadNonce])

  const details = useOnboardingProfile({ guardCompleted: false, loadSnapshot })
  const preferences = usePreferences({
    guardCompleted: false,
    successMessage: "Profile saved.",
    loadSnapshot,
  })

  const { retry: retryDetails, dismissToast: dismissDetailsToast } = details
  const { retry: retryPreferences, dismissToast: dismissPreferencesToast } = preferences

  const retryAll = useCallback(() => {
    setLoadNonce((nonce) => nonce + 1) // invalidate the shared snapshot
    retryDetails()
    retryPreferences()
  }, [retryDetails, retryPreferences])

  const cancelEditing = useCallback(() => {
    setEditing(false)
    dismissDetailsToast()
    dismissPreferencesToast()
    retryAll()
  }, [dismissDetailsToast, dismissPreferencesToast, retryAll])

  const {
    prepareSave: prepareDetails,
    applySnapshot: applyDetailsSnapshot,
    applySaveError: applyDetailsError,
  } = details
  const {
    prepareSave: preparePreferences,
    applySnapshot: applyPreferencesSnapshot,
    applySaveError: applyPreferencesError,
  } = preferences

  const saveProfile = useCallback(async () => {
    // Prepare both before bailing, so a click surfaces every invalid control
    // rather than only the first section's.
    const preparedDetails = prepareDetails()
    const preparedPreferences = preparePreferences()
    if (!preparedDetails || !preparedPreferences) return

    setSaving(true)
    try {
      const snapshot = await updateProfile({
        details: preparedDetails.payload,
        preferences: preparedPreferences,
      })
      applyDetailsSnapshot(snapshot)
      applyPreferencesSnapshot(snapshot)
      setEditing(false)
    } catch (error) {
      // A combined 422 can carry errors for both sections; each hook strips its
      // own prefix and keeps only what belongs to it.
      applyDetailsError(error, preparedDetails)
      applyPreferencesError(error)
    } finally {
      setSaving(false)
    }
  }, [
    prepareDetails,
    preparePreferences,
    applyDetailsSnapshot,
    applyPreferencesSnapshot,
    applyDetailsError,
    applyPreferencesError,
  ])

  return {
    details,
    preferences,
    /** Un-onboarded visitors get sent back into the wizard. */
    redirectTo: preferences.redirectTo,
    ready: details.status === "ready" && preferences.status === "ready",
    loading: details.status === "loading" || preferences.status === "loading",
    loadError: details.loadError ?? preferences.loadError,
    retryAll,
    editing,
    startEditing: useCallback(() => setEditing(true), []),
    cancelEditing,
    saving,
    saveProfile,
  }
}

export type ProfileEditorState = ReturnType<typeof useProfileEditor>
