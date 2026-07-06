'use client'

import { GoogleOAuthProvider } from '@react-oauth/google'
import { Check, FileText, Flag, Footprints, Search, Send, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { LucideIcon } from 'lucide-react'

import { cn } from '@/lib/utils'

type SpineNode = {
  label: string
  icon: LucideIcon
  state: 'done' | 'current' | 'upcoming'
}

const SPINE: SpineNode[] = [
  { label: 'Profile', icon: Check, state: 'done' },
  { label: 'Preferences', icon: Check, state: 'done' },
  { label: 'Search', icon: Search, state: 'current' },
  { label: 'Matches', icon: Sparkles, state: 'upcoming' },
  { label: 'Tailor', icon: FileText, state: 'upcoming' },
  { label: 'Apply', icon: Send, state: 'upcoming' },
  { label: 'Track', icon: Flag, state: 'upcoming' },
]

function JourneySpine() {
  return (
    <div className="relative mt-4">
      {/* track */}
      <div className="absolute left-0 top-4 h-1 w-full -translate-y-1/2 rounded-full bg-brand-border" />
      <div className="absolute left-0 top-4 h-1 w-[35%] -translate-y-1/2 rounded-full bg-gradient-to-r from-brand-coral to-brand-violet" />
      <ol className="relative flex items-start justify-between">
        {SPINE.map(({ label, icon: Icon, state }) => (
          <li key={label} className="flex flex-col items-center gap-2">
            <span
              className={cn(
                'flex h-8 w-8 items-center justify-center rounded-full',
                state === 'done' && 'bg-brand-emerald text-white shadow-sm',
                state === 'current' &&
                  'bg-brand-coral text-white shadow-md ring-4 ring-brand-coral/20 motion-safe:animate-pulse',
                state === 'upcoming' && 'border-2 border-brand-border bg-white text-brand-muted',
              )}
            >
              <Icon className="h-4 w-4" strokeWidth={2} />
            </span>
            <span
              className={cn(
                'font-mono text-[11px] tracking-wide',
                state === 'current' ? 'font-semibold text-brand-coral' : 'text-brand-muted',
              )}
            >
              {label}
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const onLogin = pathname?.startsWith('/login')

  const tab = (href: string, label: string, active: boolean) => (
    <Link
      href={href}
      className={cn(
        'flex-1 pb-3 text-center font-display text-xl transition-colors',
        active
          ? 'border-b-2 border-brand-violet font-semibold text-brand-violet'
          : 'border-b border-brand-border text-brand-muted hover:text-brand-ink',
      )}
    >
      {label}
    </Link>
  )

  return (
    <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!}>
      <div className="flex h-screen w-full overflow-hidden">
        {/* Left brand panel */}
        <aside className="relative hidden w-[55%] flex-col justify-between overflow-hidden bg-brand-paper p-16 lg:flex">
          <div className="absolute -right-32 -top-32 h-96 w-96 rounded-full bg-brand-violet/20 blur-3xl" />
          <div className="absolute -bottom-40 -left-32 h-[500px] w-[500px] rounded-full bg-brand-coral/10 blur-3xl" />

          <div className="z-10 flex items-center gap-2 font-display text-2xl font-semibold text-brand-violet">
            <Footprints className="h-6 w-6" />
            Hire Journey
          </div>

          <div className="z-10 max-w-lg">
            <h1 className="font-display text-5xl font-extrabold leading-tight text-brand-ink">
              Your job search,
              <br />
              <span className="bg-gradient-to-r from-brand-coral to-brand-violet bg-clip-text italic text-transparent">
                with momentum.
              </span>
            </h1>
            <p className="mt-6 max-w-md text-lg text-brand-muted">
              From resume to offer, guided the whole way. Ditch the endless applications and step
              into a structured path.
            </p>
            <div className="mt-12">
              <JourneySpine />
            </div>
          </div>

          <blockquote className="z-10 border-l-2 border-brand-violet pl-6 text-sm text-brand-muted">
            &ldquo;Finally, a tool that makes job hunting feel like progress, not a black hole.&rdquo;
            <span className="mt-1 block font-mono text-[11px] opacity-70">
              — Sarah J., Product Designer
            </span>
          </blockquote>
        </aside>

        {/* Right form panel */}
        <main className="relative z-20 flex h-full w-full flex-col items-center justify-center overflow-y-auto bg-white p-6 shadow-[-20px_0_40px_rgba(35,31,28,0.03)] md:p-12 lg:w-[45%]">
          <div className="w-full max-w-md">
            {/* Mobile logo */}
            <div className="mb-8 flex items-center gap-2 font-display text-2xl font-semibold text-brand-violet lg:hidden">
              <Footprints className="h-6 w-6" />
              Hire Journey
            </div>

            {/* Tabs = route navigation */}
            <div className="mb-8 flex">
              {tab('/register', 'Create account', !onLogin)}
              {tab('/login', 'Sign in', !!onLogin)}
            </div>

            {children}
          </div>
        </main>
      </div>
    </GoogleOAuthProvider>
  )
}
