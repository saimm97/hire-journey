import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ProfileUpdatePayload } from './types'
import { updateProfile } from './profile'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('updateProfile', () => {
  it('sends the nested update to PATCH /profile', async () => {
    const responseBody = { onboarding_complete: true }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const payload: ProfileUpdatePayload = {
      preferences: {
        minimum_salary: 90_000,
        desired_roles: ['Backend Engineer'],
        desired_locations: ['Berlin'],
        work_modes_preferred: ['remote'],
        seniority_level: 'senior',
      },
    }

    await expect(updateProfile(payload)).resolves.toEqual(responseBody)

    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toMatch(/\/api\/v1\/profile$/)
    expect(init).toMatchObject({
      method: 'PATCH',
      credentials: 'include',
      body: JSON.stringify(payload),
    })
  })
})
