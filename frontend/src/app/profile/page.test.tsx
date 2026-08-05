import type { ReactNode } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProfilePage from './page'

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  detailsRetry: vi.fn(),
  preferencesRetry: vi.fn(),
  detailsDismiss: vi.fn(),
  preferencesDismiss: vi.fn(),
  updateProfile: vi.fn(),
  prepareDetails: vi.fn(),
  preparePreferences: vi.fn(),
  applyDetailsSnapshot: vi.fn(),
  applyPreferencesSnapshot: vi.fn(),
  applyDetailsError: vi.fn(),
  applyPreferencesError: vi.fn(),
  details: {} as Record<string, unknown>,
  preferences: {} as Record<string, unknown>,
}))

vi.mock('@/lib/api/profile', () => ({
  updateProfile: mocks.updateProfile,
}))

const DETAILS_PAYLOAD = { first_name: 'Jane' }
const PREFERENCES_PAYLOAD = { desired_roles: ['Backend'] }
const PREPARED_DETAILS = {
  payload: DETAILS_PAYLOAD,
  projectPayloadIndexToUiIndex: [2],
}
const SNAPSHOT = { profile: { first_name: 'Jane' } }

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
    prepareSave: mocks.prepareDetails,
    applySnapshot: mocks.applyDetailsSnapshot,
    applySaveError: mocks.applyDetailsError,
    saveAndContinue: vi.fn(),
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
    prepareSave: mocks.preparePreferences,
    applySnapshot: mocks.applyPreferencesSnapshot,
    applySaveError: mocks.applyPreferencesError,
    save: vi.fn(),
    toast: null,
    dismissToast: mocks.preferencesDismiss,
  }
}

describe('ProfilePage read and edit modes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.details = readyDetails()
    mocks.preferences = readyPreferences()
    mocks.prepareDetails.mockReturnValue(PREPARED_DETAILS)
    mocks.preparePreferences.mockReturnValue(PREFERENCES_PAYLOAD)
    mocks.updateProfile.mockResolvedValue(SNAPSHOT)
  })

  async function openEditorAndSave(user: ReturnType<typeof userEvent.setup>) {
    await user.click(screen.getByRole('button', { name: 'Edit profile' }))
    await user.click(screen.getByRole('button', { name: 'Save profile' }))
  }

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

  it('sends both sections in a single request and returns to read mode', async () => {
    const user = userEvent.setup()
    render(<ProfilePage />)

    await openEditorAndSave(user)

    // One transaction: two requests would let details commit while
    // preferences failed, leaving a partially saved profile.
    await waitFor(() => expect(mocks.updateProfile).toHaveBeenCalledOnce())
    expect(mocks.updateProfile).toHaveBeenCalledWith({
      details: DETAILS_PAYLOAD,
      preferences: PREFERENCES_PAYLOAD,
    })
    expect(mocks.applyDetailsSnapshot).toHaveBeenCalledWith(SNAPSHOT)
    expect(mocks.applyPreferencesSnapshot).toHaveBeenCalledWith(SNAPSHOT)
    expect(screen.getByLabelText('Profile overview')).toBeVisible()
  })

  it.each([
    ['details', () => mocks.prepareDetails.mockReturnValue(null)],
    ['preferences', () => mocks.preparePreferences.mockReturnValue(null)],
  ])('sends nothing when %s fails local validation', async (_section, failSection) => {
    const user = userEvent.setup()
    failSection()
    render(<ProfilePage />)

    await openEditorAndSave(user)

    expect(mocks.updateProfile).not.toHaveBeenCalled()
    expect(screen.getByText('Details editor')).toBeVisible()
  })

  it('collects both sections before bailing so every invalid control lights up', async () => {
    const user = userEvent.setup()
    mocks.prepareDetails.mockReturnValue(null)
    render(<ProfilePage />)

    await openEditorAndSave(user)

    // Preferences is still prepared even though details already failed.
    expect(mocks.preparePreferences).toHaveBeenCalledOnce()
  })

  it('sends one request when Save is clicked twice before the first settles', async () => {
    const user = userEvent.setup()
    let release: (value: unknown) => void = () => {}
    mocks.updateProfile.mockReturnValue(new Promise((resolve) => (release = resolve)))
    render(<ProfilePage />)

    await user.click(screen.getByRole('button', { name: 'Edit profile' }))
    const save = screen.getByRole('button', { name: 'Save profile' })
    // Click is a discrete event, so React commits `savingProfile` before the
    // next one is dispatched; the second click lands on a disabled button.
    fireEvent.click(save)
    fireEvent.click(save)

    expect(mocks.updateProfile).toHaveBeenCalledOnce()
    release(SNAPSHOT)
    await waitFor(() => expect(mocks.applyDetailsSnapshot).toHaveBeenCalledOnce())
  })

  it('disables Save while the combined request is in flight', async () => {
    const user = userEvent.setup()
    let release: (value: unknown) => void = () => {}
    mocks.updateProfile.mockReturnValue(new Promise((resolve) => (release = resolve)))
    render(<ProfilePage />)

    await openEditorAndSave(user)

    expect(screen.getByRole('button', { name: 'Save profile' })).toBeDisabled()
    release(SNAPSHOT)
    await waitFor(() => expect(screen.getByLabelText('Profile overview')).toBeVisible())
  })

  it('routes a transport failure with no field errors to both sections', async () => {
    const user = userEvent.setup()
    const offline = new TypeError('Failed to fetch')
    mocks.updateProfile.mockRejectedValue(offline)
    render(<ProfilePage />)

    await openEditorAndSave(user)

    await waitFor(() => expect(mocks.applyDetailsError).toHaveBeenCalledWith(offline, PREPARED_DETAILS))
    expect(mocks.applyPreferencesError).toHaveBeenCalledWith(offline)
    expect(screen.getByText('Details editor')).toBeVisible()
  })

  it('routes a failed request to both sections and leaves the editor open', async () => {
    const user = userEvent.setup()
    const failure = new Error('422')
    mocks.updateProfile.mockRejectedValue(failure)
    render(<ProfilePage />)

    await openEditorAndSave(user)

    await waitFor(() => expect(mocks.applyDetailsError).toHaveBeenCalledOnce())
    // The prepared details carry the project index mapping the error needs.
    expect(mocks.applyDetailsError).toHaveBeenCalledWith(failure, PREPARED_DETAILS)
    expect(mocks.applyPreferencesError).toHaveBeenCalledWith(failure)
    expect(mocks.applyDetailsSnapshot).not.toHaveBeenCalled()
    expect(mocks.applyPreferencesSnapshot).not.toHaveBeenCalled()
    expect(screen.getByText('Details editor')).toBeVisible()
  })
})
