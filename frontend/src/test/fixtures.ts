/** Shared snapshot builders for onboarding tests. */

import type { CompletionIssue, OnboardingSnapshot, Profile, ResumeMeta } from '@/lib/api/types'

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
  const profile = overrides.profile ?? makeProfile()
  const sourceResume: ResumeMeta | null =
    overrides.source_resume === undefined
      ? { id: 1, file_name: 'cv.pdf', created_at: '2026-01-01T00:00:00Z', summary: null }
      : overrides.source_resume
  const completionIssues: CompletionIssue[] = overrides.onboarding_complete
    ? []
    : [
        ...(!sourceResume
          ? [{ step: 'profile' as const, path: ['source_resume'], message: 'Upload a resume.' }]
          : []),
        ...(!profile.first_name?.trim()
          ? [{ step: 'profile' as const, path: ['first_name'], message: 'Enter your first name.' }]
          : []),
        ...(!profile.last_name?.trim()
          ? [{ step: 'profile' as const, path: ['last_name'], message: 'Enter your last name.' }]
          : []),
        ...(!profile.title?.trim()
          ? [
              {
                step: 'profile' as const,
                path: ['title'],
                message: 'Enter your professional title.',
              },
            ]
          : []),
        ...(!profile.desired_roles.length
          ? [
              {
                step: 'preferences' as const,
                path: ['desired_roles'],
                message: 'Add at least one desired role.',
              },
            ]
          : []),
        ...(!profile.desired_locations.length
          ? [
              {
                step: 'preferences' as const,
                path: ['desired_locations'],
                message: 'Add at least one desired location.',
              },
            ]
          : []),
        ...(!profile.work_modes_preferred.length
          ? [
              {
                step: 'preferences' as const,
                path: ['work_modes_preferred'],
                message: 'Pick at least one work mode.',
              },
            ]
          : []),
        ...(!profile.seniority_level?.trim()
          ? [
              {
                step: 'preferences' as const,
                path: ['seniority_level'],
                message: 'Pick your seniority level.',
              },
            ]
          : []),
      ]

  return {
    profile,
    source_resume: sourceResume,
    employment_history: [],
    projects: [],
    onboarding_complete: false,
    completion_issues: completionIssues,
    ...overrides,
  }
}
