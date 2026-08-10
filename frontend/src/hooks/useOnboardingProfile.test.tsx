import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/lib/api/client'
import { makeProfile, makeSnapshot } from '@/test/fixtures'
import { MAX_UPLOAD_BYTES, useOnboardingProfile } from './useOnboardingProfile'

vi.mock('@/lib/api/profile', () => ({
  getOnboarding: vi.fn(),
  updateProfile: vi.fn(),
  uploadCv: vi.fn(),
}))

import { getOnboarding, updateProfile, uploadCv } from '@/lib/api/profile'

const getOnboardingMock = vi.mocked(getOnboarding)
const updateProfileMock = vi.mocked(updateProfile)
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

  it('hydrates the form and the read-only values the draft excludes', async () => {
    // Section mapping is covered by draftFromSnapshot; accountEmail and
    // sourceResumeId live outside ProfileDraft, so only this covers them.
    getOnboardingMock.mockResolvedValue(
      makeSnapshot({ profile: makeProfile({ phone_number: '+49 123' }) }),
    )
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    expect(result.current.identity.phone_number).toBe('+49 123')
    expect(result.current.accountEmail).toBe('jane@example.test')
  })

  it('loads once and stays settled while the draft is edited', async () => {
    // The load effect depends on `hydrate`. If that callback ever stops being
    // reference-stable the effect re-fires on every render, so pin the count.
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    const { result, rerender } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => result.current.setIdentityField('location', 'Berlin'))
    rerender()

    expect(getOnboardingMock).toHaveBeenCalledOnce()
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

  it('rejects an oversized resume before any upload', async () => {
    getOnboardingMock.mockResolvedValue(null)
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('empty'))

    const tooBig = new File(['%PDF'], 'cv.pdf', { type: 'application/pdf' })
    Object.defineProperty(tooBig, 'size', { value: MAX_UPLOAD_BYTES + 1 })
    await act(async () => {
      await result.current.uploadCv(tooBig)
    })

    expect(result.current.toast?.variant).toBe('error')
    expect(uploadCvMock).not.toHaveBeenCalled()
  })

  it('accepts a resume exactly at the size limit', async () => {
    // The check is `>`, not `>=` — the boundary is inclusive.
    getOnboardingMock.mockResolvedValue(null)
    uploadCvMock.mockResolvedValue(makeSnapshot())
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('empty'))

    const atLimit = new File(['%PDF'], 'cv.pdf', { type: 'application/pdf' })
    Object.defineProperty(atLimit, 'size', { value: MAX_UPLOAD_BYTES })
    await act(async () => {
      await result.current.uploadCv(atLimit)
    })

    expect(uploadCvMock).toHaveBeenCalledOnce()
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

  it('refuses to send an invalid draft and surfaces the errors inline', async () => {
    // The rules themselves are covered in profileDraft.test.ts; this pins that
    // an invalid draft short-circuits before any request.
    getOnboardingMock.mockResolvedValue(
      makeSnapshot({
        profile: makeProfile({ first_name: null, last_name: null, title: null }),
      }),
    )
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    let saved = true
    await act(async () => {
      saved = await result.current.saveAndContinue()
    })

    expect(saved).toBe(false)
    expect(updateProfileMock).not.toHaveBeenCalled()
    expect(result.current.toast?.variant).toBe('error')
    expect(result.current.fieldErrors.first_name).toBe('Enter your first name.')
  })

  it('maps backend validation paths to fields and clears an error when edited', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    updateProfileMock.mockRejectedValue(
      new ApiError(422, {
        message: 'Some details need fixing.',
        code: 'validation_error',
        fields: [
          {
            path: ['details', 'education', 0, 'start_date'],
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
    updateProfileMock.mockRejectedValue(
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
    updateProfileMock.mockRejectedValue(
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
    updateProfileMock.mockRejectedValue(
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

  it('sends a valid draft as the details section of one PATCH', async () => {
    // Payload shaping is covered by draftToPayload; this pins the wrapping.
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    updateProfileMock.mockResolvedValue(makeSnapshot())
    const { result } = renderHook(() => useOnboardingProfile())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => result.current.setIdentityField('location', ' Berlin '))

    let saved = false
    await act(async () => {
      saved = await result.current.saveAndContinue()
    })

    expect(saved).toBe(true)
    expect(updateProfileMock).toHaveBeenCalledOnce()
    const [body] = updateProfileMock.mock.calls[0]!
    expect(Object.keys(body)).toEqual(['details'])
    expect(body.details?.location).toBe('Berlin')
  })
})
