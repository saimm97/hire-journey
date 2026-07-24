import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/lib/api/client'
import { makeProfile, makeSnapshot } from '@/test/fixtures'
import { useOnboardingProfile } from './useOnboardingProfile'

vi.mock('@/lib/api/profile', () => ({
  getOnboarding: vi.fn(),
  saveDetails: vi.fn(),
  uploadCv: vi.fn(),
}))

import { getOnboarding, saveDetails, uploadCv } from '@/lib/api/profile'

const getOnboardingMock = vi.mocked(getOnboarding)
const saveDetailsMock = vi.mocked(saveDetails)
const uploadCvMock = vi.mocked(uploadCv)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useOnboardingProfile', () => {
  it('shows the dropzone when onboarding has not started', async () => {
    getOnboardingMock.mockResolvedValue(null)
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('empty'))
  })

  it('redirects completed users to the dashboard in wizard mode', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot({ onboarding_complete: true }))
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.redirectTo).toBe('/dashboard'))
  })

  it('edit mode hydrates completed users instead of redirecting', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot({ onboarding_complete: true }))
    const { result } = renderHook(() => useOnboardingProfile({ guardCompleted: false }))
    await waitFor(() => expect(result.current.status).toBe('ready'))
    expect(result.current.redirectTo).toBeNull()
    expect(result.current.identity.first_name).toBe('Jane')
  })

  it('hydrates every section from the snapshot', async () => {
    getOnboardingMock.mockResolvedValue(
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
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    expect(result.current.identity.phone_number).toBe('+49 123')
    expect(result.current.socialLinks.github_url).toBe('https://github.com/jane')
    expect(result.current.education.items[0]?.institution).toBe('TU Berlin')
    // API dates (YYYY-MM-DD) become month-input values (YYYY-MM)
    expect(result.current.employment.items[0]?.start_date).toBe('2021-05')
    expect(result.current.projects.items[0]?.technologies).toEqual(['langchain'])
    expect(result.current.accountEmail).toBe('jane@example.test')
  })

  it('rejects non-resume files before any upload', async () => {
    getOnboardingMock.mockResolvedValue(null)
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('empty'))

    await act(async () => {
      await result.current.uploadCv(new File(['x'], 'notes.txt', { type: 'text/plain' }))
    })
    expect(result.current.toast?.variant).toBe('error')
    expect(uploadCvMock).not.toHaveBeenCalled()
  })

  it('re-uploads replace the current source resume', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    uploadCvMock.mockResolvedValue(makeSnapshot())
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    const file = new File(['%PDF'], 'cv2.pdf', { type: 'application/pdf' })
    await act(async () => {
      await result.current.uploadCv(file)
    })
    expect(uploadCvMock).toHaveBeenCalledWith(file, 1) // source_resume_id from fixture
  })

  it('blocks saving when an employment row is missing its title', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => result.current.employment.add())
    act(() => result.current.employment.update(0, { company_name: 'Acme' }))

    let saved = true
    await act(async () => {
      saved = await result.current.saveAndContinue()
    })
    expect(saved).toBe(false)
    expect(saveDetailsMock).not.toHaveBeenCalled()
    expect(result.current.fieldErrors['employment_history.0.title']).toBe(
      'Enter the job title.',
    )
  })

  it('blocks chronologically reversed education and certification dates', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => {
      result.current.education.add()
      result.current.certifications.add()
    })
    act(() => {
      result.current.education.update(0, {
        institution: 'TU Berlin',
        start_date: '2026',
        end_date: '2012',
      })
      result.current.certifications.update(0, {
        name: 'AWS',
        issued_at: '2025-09',
        expires_at: '2025-03',
      })
    })

    let saved = true
    await act(async () => {
      saved = await result.current.saveAndContinue()
    })

    expect(saved).toBe(false)
    expect(saveDetailsMock).not.toHaveBeenCalled()
    expect(result.current.fieldErrors).toMatchObject({
      'education.0.end_date': 'The education end date cannot be before its start date.',
      'certifications.0.expires_at': 'The expiration date cannot be before its issue date.',
    })
  })

  it('names every missing core profile field before saving', async () => {
    getOnboardingMock.mockResolvedValue(
      makeSnapshot({
        profile: makeProfile({ first_name: null, last_name: null, title: null }),
      }),
    )
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    await act(async () => {
      await result.current.saveAndContinue()
    })

    expect(result.current.fieldErrors).toMatchObject({
      first_name: 'Enter your first name.',
      last_name: 'Enter your last name.',
      title: 'Enter your professional title.',
    })
    expect(saveDetailsMock).not.toHaveBeenCalled()
  })

  it('maps backend validation paths to fields and clears an error when edited', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    saveDetailsMock.mockRejectedValue(
      new ApiError(422, {
        message: 'Some details need fixing.',
        code: 'validation_error',
        fields: [
          {
            path: ['education', 0, 'start_date'],
            message: 'Use YYYY or YYYY-MM.',
          },
        ],
      }),
    )
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => result.current.education.add())
    act(() =>
      result.current.education.update(0, {
        institution: 'TU Berlin',
        start_date: '2021',
      }),
    )

    await act(async () => {
      await result.current.saveAndContinue()
    })
    expect(result.current.fieldErrors['education.0.start_date']).toBe(
      'Use YYYY or YYYY-MM.',
    )

    act(() => result.current.education.update(0, { start_date: '2021-09' }))
    expect(result.current.fieldErrors['education.0.start_date']).toBeUndefined()
  })

  it('maps a stale payload project index back to its visible row', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    saveDetailsMock.mockRejectedValue(
      new ApiError(409, {
        message: 'Your projects changed since this form was loaded.',
        code: 'projects_stale',
        fields: [
          {
            path: ['projects', 0],
            message: 'Reload the latest projects before saving.',
          },
        ],
      }),
    )
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => {
      result.current.projects.add()
      result.current.projects.add()
    })
    act(() => {
      // The empty first row is omitted from the payload, so submitted row zero
      // corresponds to visible row one.
      result.current.projects.update(1, { project_id: 42, name: 'Stale project' })
    })

    await act(async () => {
      await result.current.saveAndContinue()
    })

    expect(result.current.fieldErrors['projects.0']).toBeUndefined()
    expect(result.current.fieldErrors['projects.1']).toBe(
      'Reload the latest projects before saving.',
    )
    expect(result.current.projectConflict).toBe(
      'Your projects changed since this form was loaded.',
    )
  })

  it('reloads only projects and preserves unrelated unsaved edits', async () => {
    const initial = makeSnapshot({
      projects: [
        {
          project_id: 9,
          name: 'Original project',
          summary: 'Stored summary',
          tech_stack: [],
          github_url: null,
          deployed_url: null,
        },
      ],
    })
    const latest = makeSnapshot({
      projects: [
        {
          project_id: 10,
          name: 'Latest project',
          summary: 'Changed elsewhere',
          tech_stack: ['FastAPI'],
          github_url: null,
          deployed_url: null,
        },
      ],
    })
    getOnboardingMock.mockResolvedValueOnce(initial).mockResolvedValueOnce(latest)
    saveDetailsMock.mockRejectedValue(
      new ApiError(409, {
        message: 'Your projects changed since this form was loaded.',
        code: 'projects_stale',
        fields: [{ path: ['projects', 0], message: 'Reload the latest projects.' }],
      }),
    )
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => {
      result.current.setIdentityField('location', 'Unsaved location')
      result.current.education.add()
      result.current.projects.update(0, { summary: 'Unsaved project edit' })
    })
    act(() => {
      result.current.education.update(0, {
        institution: 'Unsaved institution',
        start_date: '2021',
      })
    })
    await act(async () => {
      await result.current.saveAndContinue()
    })

    let reloaded = false
    await act(async () => {
      reloaded = await result.current.reloadProjects()
    })

    expect(reloaded).toBe(true)
    expect(result.current.projects.items).toEqual([
      {
        project_id: 10,
        name: 'Latest project',
        summary: 'Changed elsewhere',
        technologies: ['FastAPI'],
        github_url: '',
        deployed_url: '',
      },
    ])
    expect(result.current.identity.location).toBe('Unsaved location')
    expect(result.current.education.items[0]?.institution).toBe('Unsaved institution')
    expect(result.current.fieldErrors['projects.0']).toBeUndefined()
    expect(result.current.projectConflict).toBeNull()
    expect(result.current.reloadingProjects).toBe(false)
  })

  it('keeps project edits and recovery available when project reload fails', async () => {
    const initial = makeSnapshot({
      projects: [
        {
          project_id: 9,
          name: 'Original project',
          summary: 'Stored summary',
          tech_stack: [],
          github_url: null,
          deployed_url: null,
        },
      ],
    })
    getOnboardingMock.mockResolvedValueOnce(initial).mockRejectedValueOnce(
      new ApiError(500, {
        message: 'Projects could not be loaded.',
        code: 'internal_error',
        requestId: 'request-123',
      }),
    )
    saveDetailsMock.mockRejectedValue(
      new ApiError(409, {
        message: 'Your projects changed since this form was loaded.',
        code: 'projects_stale',
        fields: [{ path: ['projects', 0], message: 'Reload the latest projects.' }],
      }),
    )
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => result.current.projects.update(0, { summary: 'Keep this edit' }))
    await act(async () => {
      await result.current.saveAndContinue()
    })

    let reloaded = true
    await act(async () => {
      reloaded = await result.current.reloadProjects()
    })

    expect(reloaded).toBe(false)
    expect(result.current.projects.items[0]?.summary).toBe('Keep this edit')
    expect(result.current.fieldErrors['projects.0']).toBe('Reload the latest projects.')
    expect(result.current.projectConflict).toBe(
      'Your projects changed since this form was loaded.',
    )
    expect(result.current.toast).toMatchObject({
      variant: 'error',
      message: 'Projects could not be loaded.',
      requestId: 'request-123',
    })
  })

  it('maps the edited state onto the exact details payload', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    saveDetailsMock.mockResolvedValue(makeSnapshot())
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => {
      result.current.setIdentityField('location', ' Berlin ')
      result.current.setSocialLink('github_url', 'github.com/jane')
      result.current.addTechnology('Python')
      result.current.employment.add()
      result.current.education.add()
    })
    act(() => {
      result.current.employment.update(0, { company_name: 'Acme', title: 'Dev', start_date: '2021-05' })
    })
    act(() => {
      result.current.projects.add()
      result.current.education.update(0, { institution: 'TU Berlin', start_date: '2021' })
    })
    // A fully empty project row is silently dropped from the payload.

    let saved = false
    await act(async () => {
      saved = await result.current.saveAndContinue()
    })

    expect(saved).toBe(true)
    const payload = saveDetailsMock.mock.calls[0]![0]
    expect(payload.location).toBe('Berlin') // trimmed
    expect(payload.social_links.github_url).toBe('github.com/jane')
    expect(payload.social_links.linkedin_url).toBeNull() // empty -> null
    expect(payload.technologies).toEqual(['Python'])
    expect(payload.employment_history).toEqual([
      {
        company_name: 'Acme',
        title: 'Dev',
        start_date: '2021-05',
        end_date: null,
        description: null,
      },
    ])
    expect(payload.education).toEqual([
      {
        institution: 'TU Berlin',
        degree: null,
        field: null,
        start_date: '2021',
        end_date: null,
      },
    ])
    expect(payload.projects).toEqual([]) // the empty row was dropped
  })
})
