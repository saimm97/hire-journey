/** Shared snapshot builders for onboarding tests. */

import type { OnboardingSnapshot, Profile } from '@/lib/api/types'

export function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 1,
    user_id: 1,
    first_name: 'Jane',
    last_name: 'Smith',
    phone_number: null,
    location: null,
    social_links: {},
    education: [],
    certifications: [],
    title: 'Backend Engineer',
    summary: null,
    minimum_salary: null,
    desired_locations: [],
    desired_roles: [],
    work_modes_preferred: [],
    seniority_level: null,
    technologies: [],
    source_resume_id: 1,
    account_email: 'jane@example.test',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeSnapshot(overrides: Partial<OnboardingSnapshot> = {}): OnboardingSnapshot {
  return {
    profile: makeProfile(),
    source_resume: { id: 1, file_name: 'cv.pdf', created_at: '2026-01-01T00:00:00Z', summary: null },
    employment_history: [],
    projects: [],
    onboarding_complete: false,
    ...overrides,
  }
}
