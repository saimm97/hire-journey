import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

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
    })
    act(() => {
      result.current.employment.update(0, { company_name: 'Acme', title: 'Dev', start_date: '2021-05' })
    })
    act(() => {
      result.current.projects.add()
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
    expect(payload.projects).toEqual([]) // the empty row was dropped
  })
})
