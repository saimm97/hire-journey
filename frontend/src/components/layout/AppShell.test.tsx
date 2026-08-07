import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AppShell } from './AppShell'

const replace = vi.fn()
const logout = vi.fn().mockResolvedValue(undefined)

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
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
    replace.mockClear()
    logout.mockClear()
  })

  it('shows the same functional destinations in desktop and mobile navigation', () => {
    render(<AppShell>Workspace</AppShell>)

    expect(screen.getAllByRole('link', { name: 'Dashboard' })).toHaveLength(2)
    expect(screen.getAllByRole('link', { name: 'Profile' })).toHaveLength(2)
    expect(screen.queryByText('Search')).not.toBeInTheDocument()
    expect(screen.queryByText('Matches')).not.toBeInTheDocument()
    expect(screen.queryByText('Applications')).not.toBeInTheDocument()
    expect(screen.queryByText('Documents')).not.toBeInTheDocument()
    expect(screen.queryByText('Start New Search')).not.toBeInTheDocument()
  })

  it('marks the active destination in both navigation variants', () => {
    render(<AppShell>Workspace</AppShell>)

    for (const link of screen.getAllByRole('link', { name: 'Dashboard' })) {
      expect(link).toHaveAttribute('aria-current', 'page')
    }
  })
})
