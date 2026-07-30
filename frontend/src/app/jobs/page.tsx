import type { Metadata } from 'next'

import { JobsBrowser } from '@/components/jobs/JobsBrowser'
import { AppShell } from '@/components/layout/AppShell'

export const metadata: Metadata = {
  title: 'Jobs — Hire Journey',
  description: 'Browse jobs collected from supported company career boards.',
}

export default function JobsPage() {
  return (
    <AppShell>
      <JobsBrowser />
    </AppShell>
  )
}
