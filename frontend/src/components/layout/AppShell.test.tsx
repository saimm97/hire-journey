import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AppShell } from './AppShell'

const replace = vi.fn()
const logout = vi.fn().mockResolvedValue(undefined)
let pathname = '/dashboard'

vi.mock('next/navigation', () => ({
  usePathname: () => pathname,
  useRouter: () => ({ replace }),
}))

vi.mock('@/lib/auth/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, username: 'sarah', email: 'sarah@example.com' },
    loading: false,
    login: vi.fn(),
    logout,
  }),
}))

describe('AppShell', () => {
  beforeEach(() => {
    pathname = '/dashboard'
    replace.mockClear()
    logout.mockClear()
  })

  it('shows the same functional destinations in desktop and mobile navigation', () => {
    render(<AppShell>Workspace</AppShell>)

    expect(screen.getAllByRole('link', { name: 'Dashboard' })).toHaveLength(2)
    expect(screen.getAllByRole('link', { name: 'Jobs' })).toHaveLength(2)
    expect(screen.getAllByRole('link', { name: 'Profile' })).toHaveLength(2)
    expect(screen.queryByText('Search')).not.toBeInTheDocument()
    expect(screen.queryByText('Matches')).not.toBeInTheDocument()
    expect(screen.queryByText('Applications')).not.toBeInTheDocument()
    expect(screen.queryByText('Documents')).not.toBeInTheDocument()
    expect(screen.queryByText('Start New Search')).not.toBeInTheDocument()
  })

  it('marks the active destination in both navigation variants', () => {
    pathname = '/jobs'
    render(<AppShell>Workspace</AppShell>)

    for (const link of screen.getAllByRole('link', { name: 'Jobs' })) {
      expect(link).toHaveAttribute('aria-current', 'page')
    }
  })
})
