import { describe, expect, it } from 'vitest'

import { makeProfile, makeSnapshot } from '@/test/fixtures'
import {
  appendTechnology,
  draftFromSnapshot,
  draftToPayload,
  emptyEducation,
  emptyProject,
  remapProjectRow,
  validateDraft,
  type ProfileDraft,
} from './profileDraft'

/** A draft that passes validation, so each test can vary one thing. */
const validDraft = (overrides: Partial<ProfileDraft> = {}): ProfileDraft => ({
  identity: {
    first_name: 'Jane',
    last_name: 'Smith',
    phone_number: '',
    location: '',
    title: 'Backend Engineer',
  },
  socialLinks: { github_url: '', linkedin_url: '', portfolio_url: '' },
  summary: '',
  technologies: [],
  education: [],
  certifications: [],
  employment: [],
  projects: [],
  ...overrides,
})

describe('draftFromSnapshot', () => {
  it('maps every section of a saved snapshot', () => {
    const draft = draftFromSnapshot(
      makeSnapshot({
        profile: makeProfile({
          phone_number: '+49 123',
          social_links: { github_url: 'https://github.com/jane' },
          education: [{ institution: 'TU Berlin', degree: 'BSc' }],
          technologies: ['python'],
        }),
        employment_history: [
          {
            id: 5,
            company_name: 'Acme',
            title: 'Dev',
            start_date: '2021-05-01',
            end_date: null,
            description: null,
          },
        ],
        projects: [
          {
            project_id: 9,
            name: 'Career Engine',
            summary: null,
            tech_stack: ['langchain'],
            github_url: null,
            deployed_url: null,
          },
        ],
      }),
    )

    expect(draft.identity.phone_number).toBe('+49 123')
    expect(draft.socialLinks.github_url).toBe('https://github.com/jane')
    expect(draft.education[0]?.institution).toBe('TU Berlin')
    expect(draft.technologies).toEqual(['python'])
    expect(draft.projects[0]?.technologies).toEqual(['langchain'])
    // API dates (YYYY-MM-DD) become month-input values (YYYY-MM).
    expect(draft.employment[0]?.start_date).toBe('2021-05')
  })

  it('turns every absent value into an empty string, never null', () => {
    const draft = draftFromSnapshot(
      makeSnapshot({
        profile: makeProfile({ first_name: null, summary: null, social_links: {} }),
        employment_history: [
          {
            id: 1,
            company_name: 'Acme',
            title: 'Dev',
            start_date: null,
            end_date: null,
            description: null,
          },
        ],
      }),
    )

    expect(draft.identity.first_name).toBe('')
    expect(draft.summary).toBe('')
    expect(draft.socialLinks.linkedin_url).toBe('')
    expect(draft.employment[0]?.end_date).toBe('')
  })

  it('copies array values so the draft never aliases the fetched snapshot', () => {
    const snapshot = makeSnapshot({
      profile: makeProfile({ technologies: ['python'] }),
      projects: [
        {
          project_id: 9,
          name: 'P',
          summary: null,
          tech_stack: ['rust'],
          github_url: null,
          deployed_url: null,
        },
      ],
    })
    const draft = draftFromSnapshot(snapshot)

    expect(draft.technologies).not.toBe(snapshot.profile.technologies)
    expect(draft.projects[0]?.technologies).not.toBe(snapshot.projects[0]?.tech_stack)
  })
})

describe('validateDraft', () => {
  it('names every missing core profile field', () => {
    const errors = validateDraft(
      validDraft({ identity: { ...validDraft().identity, first_name: '', last_name: '', title: '' } }),
    )

    expect(errors).toMatchObject({
      first_name: 'Enter your first name.',
      last_name: 'Enter your last name.',
      title: 'Enter your professional title.',
    })
  })

  it('requires a title on an employment row the user started', () => {
    const errors = validateDraft(
      validDraft({
        employment: [{ company_name: 'Acme', title: '', start_date: '', end_date: '', description: '' }],
      }),
    )

    expect(errors['employment_history.0.title']).toBe('Enter the job title.')
  })

  it('ignores rows the user never typed into', () => {
    expect(validateDraft(validDraft({ education: [emptyEducation()] }))).toEqual({})
  })

  it('rejects chronologically reversed education and certification dates', () => {
    const errors = validateDraft(
      validDraft({
        education: [
          { institution: 'TU Berlin', degree: '', field: '', start_date: '2026', end_date: '2012' },
        ],
        certifications: [
          { name: 'AWS', issuer: '', issued_at: '2025-09', expires_at: '2025-03' },
        ],
      }),
    )

    expect(errors).toMatchObject({
      'education.0.end_date': 'The education end date cannot be before its start date.',
      'certifications.0.expires_at': 'The expiration date cannot be before its issue date.',
    })
  })

  it('accepts a same-year range when only one side carries a month', () => {
    // Year-only precision is intentionally unknown, so this is not reversed.
    const errors = validateDraft(
      validDraft({
        education: [
          { institution: 'TU Berlin', degree: '', field: '', start_date: '2021-09', end_date: '2021' },
        ],
      }),
    )

    expect(errors).toEqual({})
  })

  it('builds keys in on-screen order, because the caller focuses the first one', () => {
    const errors = validateDraft(
      validDraft({
        identity: { ...validDraft().identity, first_name: '', title: '' },
        education: [{ institution: '', degree: 'BSc', field: '', start_date: '', end_date: '' }],
      }),
    )

    expect(Object.keys(errors)).toEqual(['first_name', 'title', 'education.0.institution'])
  })
})

describe('draftToPayload', () => {
  it('trims, nulls empties, and drops blank rows', () => {
    const { payload } = draftToPayload(
      validDraft({
        identity: { ...validDraft().identity, location: ' Berlin ' },
        socialLinks: { github_url: 'github.com/jane', linkedin_url: '', portfolio_url: '' },
        technologies: ['Python'],
        employment: [
          { company_name: 'Acme', title: 'Dev', start_date: '2021-05', end_date: '', description: '' },
        ],
        education: [
          { institution: 'TU Berlin', degree: '', field: '', start_date: '2021', end_date: '' },
        ],
        projects: [emptyProject()],
      }),
    )

    expect(payload.location).toBe('Berlin')
    expect(payload.social_links.github_url).toBe('github.com/jane')
    expect(payload.social_links.linkedin_url).toBeNull()
    expect(payload.technologies).toEqual(['Python'])
    expect(payload.employment_history).toEqual([
      { company_name: 'Acme', title: 'Dev', start_date: '2021-05', end_date: null, description: null },
    ])
    expect(payload.education).toEqual([
      { institution: 'TU Berlin', degree: null, field: null, start_date: '2021', end_date: null },
    ])
    expect(payload.projects).toEqual([])
  })

  it('maps payload project indices back to the rows the user can see', () => {
    const { payload, projectPayloadIndexToUiIndex } = draftToPayload(
      validDraft({
        projects: [emptyProject(), { ...emptyProject(), project_id: 42, name: 'Real' }],
      }),
    )

    // The blank row 0 is dropped, so payload index 0 is visible row 1.
    expect(payload.projects).toHaveLength(1)
    expect(projectPayloadIndexToUiIndex).toEqual([1])
  })

  it('treats a row carrying only project_id as blank', () => {
    // project_id is a number, so hasContent sees nothing the user typed.
    const { payload } = draftToPayload(
      validDraft({ projects: [{ ...emptyProject(), project_id: 42 }] }),
    )

    expect(payload.projects).toEqual([])
  })
})

describe('appendTechnology', () => {
  it('trims and appends a new value', () => {
    expect(appendTechnology(['Python'], '  Go  ')).toEqual(['Python', 'Go'])
  })

  it('ignores a case-insensitive duplicate', () => {
    const existing = ['Python']
    expect(appendTechnology(existing, 'python')).toBe(existing)
  })

  it('ignores blank input', () => {
    const existing = ['Python']
    expect(appendTechnology(existing, '   ')).toBe(existing)
  })
})

describe('remapProjectRow', () => {
  it('rewrites a project row index and keeps the rest of the path', () => {
    const remap = remapProjectRow([1])

    expect(remap(['projects', 0])).toEqual(['projects', 1])
    expect(remap(['projects', 0, 'name'])).toEqual(['projects', 1, 'name'])
  })

  it('passes through paths it does not own', () => {
    const remap = remapProjectRow([1])

    expect(remap(['education', 0])).toEqual(['education', 0])
    expect(remap(['projects', 5])).toEqual(['projects', 5]) // out of range
    expect(remapProjectRow([])(['projects', 0])).toEqual(['projects', 0])
  })

  it('never mutates the path it was given', () => {
    const path: Array<string | number> = ['projects', 0, 'name']
    remapProjectRow([1])(path)

    expect(path).toEqual(['projects', 0, 'name'])
  })
})
