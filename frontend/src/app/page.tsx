'use client'

import { Loader2, LogOut } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth/AuthContext'

export default function Home() {
  const router = useRouter()
  const { user, loading, logout } = useAuth()

  async function handleLogout() {
    await logout() // clear session cookie on backend and reset client state
    router.push('/login')
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center bg-brand-paper">
        <Loader2 className="h-6 w-6 animate-spin text-brand-primary" />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 bg-brand-paper">
        <p className="text-brand-muted">You&apos;re not signed in.</p>
        <Link href="/login" className="font-semibold text-brand-primary hover:underline">
          Go to sign in →
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-1 items-center justify-center bg-brand-paper p-6">
      <div className="w-full max-w-md rounded-xl border border-brand-border bg-white p-8">
        <h1 className="text-[32px] font-semibold leading-10 tracking-tight text-brand-ink">
          Welcome back, {user.username}
        </h1>
        <p className="mt-2 text-brand-muted">{user.email}</p>
        <Button onClick={handleLogout} size="lg" className="mt-8">
          <LogOut className="h-4 w-4" />
          Log out
        </Button>
      </div>
    </div>
  )
}
