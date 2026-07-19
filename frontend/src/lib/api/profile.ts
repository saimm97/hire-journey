import { ApiError, apiRequest } from './client'
import type {
  OnboardingSnapshot,
  PreferencesPayload,
  ProfileDetailsPayload,
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
  return apiRequest<OnboardingSnapshot>(`/profile/cv${query}`, { method: 'POST', body })
}

/** Save the corrected details step (full replacement of profile-owned collections). */
export function saveDetails(payload: ProfileDetailsPayload): Promise<OnboardingSnapshot> {
  return apiRequest<OnboardingSnapshot>('/profile/details', { method: 'PUT', body: payload })
}

/** Save the preferences step; the returned snapshot carries the fresh completion state. */
export function savePreferences(payload: PreferencesPayload): Promise<OnboardingSnapshot> {
  return apiRequest<OnboardingSnapshot>('/profile/preferences', {
    method: 'PUT',
    body: payload,
  })
}
