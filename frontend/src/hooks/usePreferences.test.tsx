import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { makeProfile, makeSnapshot } from '@/test/fixtures'
import { usePreferences } from './usePreferences'

vi.mock('@/lib/api/profile', () => ({
  getOnboarding: vi.fn(),
  savePreferences: vi.fn(),
}))

import { getOnboarding, savePreferences } from '@/lib/api/profile'

const getOnboardingMock = vi.mocked(getOnboarding)
const savePreferencesMock = vi.mocked(savePreferences)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('usePreferences', () => {
  it('hydrates from the snapshot', async () => {
    getOnboardingMock.mockResolvedValue(
      makeSnapshot({
        profile: makeProfile({
          desired_roles: ['Backend'],
          desired_locations: ['Berlin'],
          work_modes_preferred: ['remote', 'bogus'],
          seniority_level: 'senior',
          minimum_salary: 90000,
        }),
      }),
    )
    const { result } = renderHook(() => usePreferences())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    expect(result.current.roles).toEqual(['Backend'])
    expect(result.current.locations).toEqual(['Berlin'])
    expect(result.current.workModes).toEqual(['remote']) // unknown values dropped
    expect(result.current.seniority).toBe('senior')
    expect(result.current.minimumSalary).toBe(90000)
  })

  it('redirects to the profile step without a source resume', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot({ source_resume: null }))
    const { result } = renderHook(() => usePreferences())
    await waitFor(() => expect(result.current.redirectTo).toBe('/onboarding/profile'))
  })

  it('redirects completed users into the app', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot({ onboarding_complete: true }))
    const { result } = renderHook(() => usePreferences())
    await waitFor(() => expect(result.current.redirectTo).toBe('/'))
  })

  it('blocks saving until the step requirements are met', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    const { result } = renderHook(() => usePreferences())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    let saved = true
    await act(async () => {
      saved = await result.current.save()
    })
    expect(saved).toBe(false)
    expect(result.current.toast?.variant).toBe('error')
    expect(savePreferencesMock).not.toHaveBeenCalled()
  })

  it('sends the exact preferences payload and reports completion', async () => {
    getOnboardingMock.mockResolvedValue(makeSnapshot())
    savePreferencesMock.mockResolvedValue(makeSnapshot({ onboarding_complete: true }))
    const { result } = renderHook(() => usePreferences())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => {
      result.current.addRole('Backend Engineer')
      result.current.addRole('backend engineer ') // case-insensitive dedupe
      result.current.addLocation('Berlin')
      result.current.toggleWorkMode('remote')
      result.current.setSeniority('senior')
      result.current.setMinimumSalary(90000)
    })

    let saved = false
    await act(async () => {
      saved = await result.current.save()
    })

    expect(saved).toBe(true)
    expect(savePreferencesMock).toHaveBeenCalledWith({
      minimum_salary: 90000,
      desired_roles: ['Backend Engineer'],
      desired_locations: ['Berlin'],
      work_modes_preferred: ['remote'],
      seniority_level: 'senior',
    })
  })
})
