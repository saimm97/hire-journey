import type { ReactNode } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProfilePage from './page'

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  detailsRetry: vi.fn(),
  preferencesRetry: vi.fn(),
  detailsDismiss: vi.fn(),
  preferencesDismiss: vi.fn(),
  saveDetails: vi.fn(),
  savePreferences: vi.fn(),
  details: {} as Record<string, unknown>,
  preferences: {} as Record<string, unknown>,
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mocks.replace }),
}))

vi.mock('@/components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/profile/ProfileOverview', () => ({
  ProfileOverview: () => <div aria-label="Profile overview">Saved profile</div>,
}))

vi.mock('@/components/onboarding/ProfileForm', () => ({
  ProfileForm: () => <div>Details editor</div>,
}))

vi.mock('@/components/onboarding/PreferencesForm', () => ({
  PreferencesForm: () => <div>Preferences editor</div>,
}))

vi.mock('@/components/onboarding/OnboardingLoadError', () => ({
  OnboardingLoadError: () => <div>Load error</div>,
}))

vi.mock('@/components/onboarding/ResumeDropzone', () => ({
  ResumeDropzone: () => <div>Resume upload</div>,
}))

vi.mock('@/components/onboarding/Toast', () => ({
  Toast: () => null,
}))

vi.mock('@/hooks/useOnboardingProfile', () => ({
  useOnboardingProfile: () => mocks.details,
}))

vi.mock('@/hooks/usePreferences', () => ({
  usePreferences: () => mocks.preferences,
}))

function readyDetails() {
  return {
    status: 'ready',
    redirectTo: null,
    loadError: null,
    retry: mocks.detailsRetry,
    identity: {
      first_name: 'Jane',
      last_name: 'Smith',
      phone_number: '',
      location: '',
      title: 'Engineer',
    },
    accountEmail: 'jane@example.test',
    socialLinks: { github_url: '', linkedin_url: '', portfolio_url: '' },
    summary: '',
    technologies: [],
    employment: { items: [] },
    education: { items: [] },
    certifications: { items: [] },
    projects: { items: [] },
    saving: false,
    saveAndContinue: mocks.saveDetails,
    uploadCv: vi.fn(),
    toast: null,
    dismissToast: mocks.detailsDismiss,
  }
}

function readyPreferences() {
  return {
    status: 'ready',
    redirectTo: null,
    loadError: null,
    retry: mocks.preferencesRetry,
    roles: [],
    locations: [],
    workModes: [],
    seniority: null,
    minimumSalary: null,
    saving: false,
    save: mocks.savePreferences,
    toast: null,
    dismissToast: mocks.preferencesDismiss,
  }
}

describe('ProfilePage read and edit modes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.details = readyDetails()
    mocks.preferences = readyPreferences()
    mocks.saveDetails.mockResolvedValue(true)
    mocks.savePreferences.mockResolvedValue(true)
  })

  it('starts in read mode and enters the existing editors on demand', async () => {
    const user = userEvent.setup()
    render(<ProfilePage />)

    expect(screen.getByLabelText('Profile overview')).toBeVisible()
    expect(screen.queryByText('Details editor')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Edit profile' }))

    expect(screen.getByText('Details editor')).toBeVisible()
    expect(screen.getByText('Preferences editor')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Save profile' })).toBeVisible()
  })

  it('cancels by reloading both saved aggregates before returning to read mode', async () => {
    const user = userEvent.setup()
    render(<ProfilePage />)

    await user.click(screen.getByRole('button', { name: 'Edit profile' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(mocks.detailsRetry).toHaveBeenCalledOnce()
    expect(mocks.preferencesRetry).toHaveBeenCalledOnce()
    expect(mocks.detailsDismiss).toHaveBeenCalledOnce()
    expect(mocks.preferencesDismiss).toHaveBeenCalledOnce()
    expect(screen.getByLabelText('Profile overview')).toBeVisible()
  })

  it('saves details before preferences and returns to read mode only after both succeed', async () => {
    const user = userEvent.setup()
    render(<ProfilePage />)

    await user.click(screen.getByRole('button', { name: 'Edit profile' }))
    await user.click(screen.getByRole('button', { name: 'Save profile' }))

    await waitFor(() => expect(mocks.savePreferences).toHaveBeenCalledOnce())
    expect(mocks.saveDetails.mock.invocationCallOrder[0]).toBeLessThan(
      mocks.savePreferences.mock.invocationCallOrder[0],
    )
    expect(screen.getByLabelText('Profile overview')).toBeVisible()
  })

  it('keeps the editor and existing inline-error surface when details do not save', async () => {
    const user = userEvent.setup()
    mocks.saveDetails.mockResolvedValue(false)
    render(<ProfilePage />)

    await user.click(screen.getByRole('button', { name: 'Edit profile' }))
    await user.click(screen.getByRole('button', { name: 'Save profile' }))

    await waitFor(() => expect(mocks.saveDetails).toHaveBeenCalledOnce())
    expect(mocks.savePreferences).not.toHaveBeenCalled()
    expect(screen.getByText('Details editor')).toBeVisible()
  })
})
