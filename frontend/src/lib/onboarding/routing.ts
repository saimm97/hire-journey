import { getOnboarding } from '@/lib/api/profile'
import type { OnboardingSnapshot } from '@/lib/api/types'

/** Where fully-onboarded users land. */
export const COMPLETED_DESTINATION = '/dashboard'

/**
 * The single routing rule for onboarding — used by the post-auth redirect and
 * by the onboarding pages' own guards, so the decision never diverges.
 */
export function onboardingDestination(snapshot: OnboardingSnapshot | null): string {
  if (!snapshot || !snapshot.source_resume) return '/onboarding/profile'
  if (snapshot.onboarding_complete) return COMPLETED_DESTINATION
  if (snapshot.completion_issues?.some((issue) => issue.step === 'profile'))
    return '/onboarding/profile'

  // Compatibility with snapshots produced during a rolling backend deployment.
  if (!snapshot.completion_issues) {
    const { first_name, last_name, title } = snapshot.profile
    if (!first_name?.trim() || !last_name?.trim() || !title?.trim())
      return '/onboarding/profile'
  }
  return '/onboarding/preferences'
}

/** Where to send the user after authenticating. Never blocks login on an API hiccup. */
export async function postAuthDestination(): Promise<string> {
  try {
    return onboardingDestination(await getOnboarding())
  } catch {
    return COMPLETED_DESTINATION
  }
}
