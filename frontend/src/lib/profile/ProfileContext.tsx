"use client"

import { getOnboarding } from "@/lib/api/profile"
import type { OnboardingSnapshot } from "@/lib/api/types"
import { createResourceContext } from "@/lib/data/createResourceContext"

/**
 * App-wide cache of the user's onboarding snapshot (profile + resume +
 * employment + projects + completion). Fetched once by ProfileProvider and
 * read anywhere via useProfileResource (see the useProfile hook for the
 * friendlier shape).
 */
const { Provider, useResource } = createResourceContext<OnboardingSnapshot>(
  getOnboarding,
  "Profile",
)

export const ProfileProvider = Provider
export const useProfileResource = useResource
