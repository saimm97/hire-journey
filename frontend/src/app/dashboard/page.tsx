import Link from 'next/link'

import { AppShell } from '@/components/layout/AppShell'

export const metadata = { title: 'Dashboard — Hire Journey' }

/** Placeholder until the dashboard design lands — onboarding redirects here. */
export default function Dashboard() {
  return (
    <AppShell active="dashboard">
      <div className="flex flex-col items-center justify-center gap-4 py-32 text-center">
        <h1 className="font-display text-3xl font-semibold text-brand-ink">Dashboard</h1>
        <p className="max-w-md text-brand-muted">
          Your job matches will land here soon. Meanwhile, keep your profile sharp.
        </p>
        <Link
          href="/profile"
          className="rounded-full bg-brand-coral px-6 py-2.5 font-semibold text-white shadow-sm transition-colors hover:bg-brand-coral-dark"
        >
          Edit profile
        </Link>
      </div>
    </AppShell>
  )
}
