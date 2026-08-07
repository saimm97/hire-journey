import { WelcomeBanner } from '@/components/dashboard/WelcomeBanner'
import { AppShell } from '@/components/layout/AppShell'

export const metadata = { title: 'Dashboard — Hire Journey' }

export default function Dashboard() {
  return (
    <AppShell>
      <WelcomeBanner />
    </AppShell>
  )
}
