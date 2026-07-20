import type { ReactNode } from 'react'

import { AppShell } from '@/components/layout/AppShell'
import { ProfileProvider } from '@/lib/profile/ProfileContext'

/**
 * Chrome + data for the authenticated app. As a route layout it persists
 * across navigation between its pages, so ProfileProvider fetches the
 * snapshot exactly once and the sidebar never remounts.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <ProfileProvider>
      <AppShell>{children}</AppShell>
    </ProfileProvider>
  )
}
