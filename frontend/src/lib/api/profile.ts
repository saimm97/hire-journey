import { ApiError, apiRequest } from './client'
import type {
  OnboardingSnapshot,
  ProfileUpdatePayload,
} from './types'

/** The onboarding snapshot, or null when onboarding hasn't started yet (404). */
export async function getOnboarding(): Promise<OnboardingSnapshot | null> {
  try {
    return await apiRequest<OnboardingSnapshot>('/profile')
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

/** Upload a resume (PDF/DOCX). Passing replaceResumeId overwrites that resume in place. */
export function uploadCv(
  file: File,
  replaceResumeId?: number | null,
): Promise<OnboardingSnapshot> {
  const body = new FormData()
  body.append('file', file)
  const query = replaceResumeId ? `?replace_resume_id=${replaceResumeId}` : ''
  // Parsing + LLM extraction runs synchronously in this request; allow more time.
  return apiRequest<OnboardingSnapshot>(`/profile/cv${query}`, {
    method: 'POST',
    body,
    timeoutMs: 120_000,
  })
}

/** Update one or both complete profile sections and return the refreshed snapshot. */
export function updateProfile(payload: ProfileUpdatePayload): Promise<OnboardingSnapshot> {
  return apiRequest<OnboardingSnapshot>('/profile', {
    method: 'PATCH',
    body: payload,
  })
}
