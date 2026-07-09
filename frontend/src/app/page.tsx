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
        <Loader2 className="h-6 w-6 animate-spin text-brand-violet" />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 bg-brand-paper">
        <p className="text-brand-muted">You&apos;re not signed in.</p>
        <Link href="/login" className="font-semibold text-brand-violet hover:underline">
          Go to sign in →
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-1 items-center justify-center bg-brand-paper p-6">
      <div className="w-full max-w-md rounded-2xl border border-brand-border bg-white p-8 shadow-sm">
        <h1 className="font-display text-3xl font-bold text-brand-ink">
          Welcome back, {user.username}
        </h1>
        <p className="mt-2 text-brand-muted">{user.email}</p>
        <Button
          onClick={handleLogout}
          className="mt-8 h-11 rounded-full bg-brand-violet font-semibold text-white hover:bg-brand-violet-dark"
        >
          <LogOut className="h-4 w-4" />
          Log out
        </Button>
      </div>
    </div>
  )
}
