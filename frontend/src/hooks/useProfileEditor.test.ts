import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/lib/api/client'
import { makeProfile, makeSnapshot } from '@/test/fixtures'
import { useProfileEditor } from './useProfileEditor'

vi.mock('@/lib/api/profile', () => ({
  getOnboarding: vi.fn(),
  updateProfile: vi.fn(),
  uploadCv: vi.fn(),
}))

import { getOnboarding, updateProfile } from '@/lib/api/profile'

const getOnboardingMock = vi.mocked(getOnboarding)
const updateProfileMock = vi.mocked(updateProfile)

/** A profile complete enough that both sections pass local validation. */
const completeSnapshot = () =>
  makeSnapshot({
    onboarding_complete: true,
    profile: makeProfile({
      desired_roles: ['Backend Engineer'],
      desired_locations: ['Berlin'],
      work_modes_preferred: ['remote'],
      seniority_level: 'senior',
    }),
  })

const renderReady = async () => {
  const rendered = renderHook(() => useProfileEditor())
  await waitFor(() => expect(rendered.result.current.ready).toBe(true))
  return rendered
}

beforeEach(() => {
  vi.clearAllMocks()
  getOnboardingMock.mockResolvedValue(completeSnapshot())
  updateProfileMock.mockResolvedValue(completeSnapshot())
})

describe('useProfileEditor', () => {
  it('reads the snapshot once for both sections', async () => {
    // Both hooks hydrate from the same aggregate; two mounts must not mean two GETs.
    const { result } = await renderReady()

    expect(getOnboardingMock).toHaveBeenCalledOnce()
    expect(result.current.details.identity.first_name).toBe('Jane')
    expect(result.current.preferences.roles).toEqual(['Backend Engineer'])
  })

  it('refetches when retried rather than replaying the cached snapshot', async () => {
    const { result } = await renderReady()

    act(() => result.current.retryAll())
    await waitFor(() => expect(result.current.ready).toBe(true))

    expect(getOnboardingMock).toHaveBeenCalledTimes(2)
  })

  it('sends both sections in one PATCH and leaves edit mode', async () => {
    const { result } = await renderReady()
    act(() => result.current.startEditing())

    await act(async () => {
      await result.current.saveProfile()
    })

    expect(updateProfileMock).toHaveBeenCalledOnce()
    const [body] = updateProfileMock.mock.calls[0]!
    expect(Object.keys(body).sort()).toEqual(['details', 'preferences'])
    expect(body.details?.first_name).toBe('Jane')
    expect(body.preferences?.desired_roles).toEqual(['Backend Engineer'])
    expect(result.current.editing).toBe(false)
  })

  it('sends nothing when a section fails local validation', async () => {
    getOnboardingMock.mockResolvedValue(
      makeSnapshot({
        onboarding_complete: true,
        profile: makeProfile({
          title: null, // details is now invalid
          desired_roles: ['Backend Engineer'],
          desired_locations: ['Berlin'],
          work_modes_preferred: ['remote'],
          seniority_level: 'senior',
        }),
      }),
    )
    const { result } = await renderReady()
    act(() => result.current.startEditing())

    await act(async () => {
      await result.current.saveProfile()
    })

    expect(updateProfileMock).not.toHaveBeenCalled()
    expect(result.current.editing).toBe(true)
    expect(result.current.details.fieldErrors.title).toBe('Enter your professional title.')
    // Preferences was still prepared, so every invalid control lights up at once.
    expect(result.current.preferences.fieldErrors).toEqual({})
  })

  it('routes a combined 422 to whichever section owns each field', async () => {
    updateProfileMock.mockRejectedValue(
      new ApiError(422, {
        message: 'Some details need fixing.',
        code: 'validation_error',
        fields: [
          { path: ['details', 'first_name'], message: 'Enter your first name.' },
          { path: ['preferences', 'desired_roles'], message: 'Add at least one desired role.' },
        ],
      }),
    )
    const { result } = await renderReady()
    act(() => result.current.startEditing())

    await act(async () => {
      await result.current.saveProfile()
    })

    expect(result.current.details.fieldErrors.first_name).toBe('Enter your first name.')
    expect(result.current.preferences.fieldErrors.desired_roles).toBe(
      'Add at least one desired role.',
    )
    // Neither section's error leaks into the other.
    expect(result.current.details.fieldErrors.desired_roles).toBeUndefined()
    expect(result.current.preferences.fieldErrors.first_name).toBeUndefined()
    expect(result.current.editing).toBe(true)
  })

  it('stays in edit mode when the request fails outright', async () => {
    updateProfileMock.mockRejectedValue(new TypeError('Failed to fetch'))
    const { result } = await renderReady()
    act(() => result.current.startEditing())

    await act(async () => {
      await result.current.saveProfile()
    })

    expect(result.current.editing).toBe(true)
    expect(result.current.details.toast?.variant).toBe('error')
  })

  it('cancelling reloads both saved sections and leaves edit mode', async () => {
    const { result } = await renderReady()
    act(() => result.current.startEditing())
    act(() => result.current.details.setIdentityField('first_name', 'Discarded'))

    act(() => result.current.cancelEditing())
    await waitFor(() => expect(result.current.ready).toBe(true))

    expect(result.current.editing).toBe(false)
    expect(result.current.details.identity.first_name).toBe('Jane')
  })
})
