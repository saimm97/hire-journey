import { getOnboarding } from '@/lib/api/profile'
import type { OnboardingSnapshot } from '@/lib/api/types'

/**
 * The single routing rule for onboarding — used by the post-auth redirect and
 * by the onboarding pages' own guards, so the decision never diverges.
 */
export function onboardingDestination(snapshot: OnboardingSnapshot | null): string {
  if (!snapshot || !snapshot.source_resume) return '/onboarding/profile'
  if (snapshot.onboarding_complete) return '/'
  const { first_name, last_name, title } = snapshot.profile
  const detailsDone = Boolean(first_name?.trim() && last_name?.trim() && title?.trim())
  return detailsDone ? '/onboarding/preferences' : '/onboarding/profile'
}

/** Where to send the user after authenticating. Never blocks login on an API hiccup. */
export async function postAuthDestination(): Promise<string> {
  try {
    return onboardingDestination(await getOnboarding())
  } catch {
    return '/'
  }
}
