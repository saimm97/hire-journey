import type { ReactNode } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProfilePage from './page'

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  retryAll: vi.fn(),
  startEditing: vi.fn(),
  cancelEditing: vi.fn(),
  saveProfile: vi.fn(),
  editor: {} as Record<string, unknown>,
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

vi.mock('@/hooks/useProfileEditor', () => ({
  useProfileEditor: () => mocks.editor,
}))

/** The editor surface this page renders; orchestration is covered by its own hook. */
function readyEditor(overrides: Record<string, unknown> = {}) {
  return {
    details: {
      status: 'ready',
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
      uploadCv: vi.fn(),
      toast: null,
      dismissToast: vi.fn(),
    },
    preferences: {
      roles: [],
      locations: [],
      workModes: [],
      seniority: null,
      minimumSalary: null,
      toast: null,
      dismissToast: vi.fn(),
    },
    redirectTo: null,
    ready: true,
    loading: false,
    loadError: null,
    retryAll: mocks.retryAll,
    editing: false,
    startEditing: mocks.startEditing,
    cancelEditing: mocks.cancelEditing,
    saving: false,
    saveProfile: mocks.saveProfile,
    ...overrides,
  }
}

describe('ProfilePage read and edit modes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.editor = readyEditor()
  })

  it('starts in read mode and opens the editors on demand', async () => {
    const user = userEvent.setup()
    render(<ProfilePage />)

    expect(screen.getByLabelText('Profile overview')).toBeVisible()
    expect(screen.queryByText('Details editor')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Edit profile' }))

    expect(mocks.startEditing).toHaveBeenCalledOnce()
  })

  it('renders both editors and the save control while editing', () => {
    mocks.editor = readyEditor({ editing: true })
    render(<ProfilePage />)

    expect(screen.getByText('Details editor')).toBeVisible()
    expect(screen.getByText('Preferences editor')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Save profile' })).toBeVisible()
    expect(screen.queryByLabelText('Profile overview')).not.toBeInTheDocument()
  })

  it('wires Save and Cancel to the editor', async () => {
    const user = userEvent.setup()
    mocks.editor = readyEditor({ editing: true })
    render(<ProfilePage />)

    await user.click(screen.getByRole('button', { name: 'Save profile' }))
    expect(mocks.saveProfile).toHaveBeenCalledOnce()

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(mocks.cancelEditing).toHaveBeenCalledOnce()
  })

  it('disables Save while a combined save is in flight', () => {
    mocks.editor = readyEditor({ editing: true, saving: true })
    render(<ProfilePage />)

    expect(screen.getByRole('button', { name: 'Save profile' })).toBeDisabled()
  })

  it('sends no further save when Save is clicked again mid-flight', () => {
    // The disabled attribute is the guard; clicking through it must not re-fire.
    mocks.editor = readyEditor({ editing: true, saving: true })
    render(<ProfilePage />)

    const save = screen.getByRole('button', { name: 'Save profile' })
    fireEvent.click(save)
    fireEvent.click(save)

    expect(mocks.saveProfile).not.toHaveBeenCalled()
  })

  it('redirects visitors who have not onboarded', () => {
    mocks.editor = readyEditor({ redirectTo: '/onboarding/profile' })
    render(<ProfilePage />)

    expect(mocks.replace).toHaveBeenCalledWith('/onboarding/profile')
  })

  it('offers a retry when either section fails to load', () => {
    mocks.editor = readyEditor({ ready: false, loading: false, loadError: 'Nope.' })
    render(<ProfilePage />)

    expect(screen.getByText('Load error')).toBeVisible()
  })
})
