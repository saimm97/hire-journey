'use client'

import { GoogleOAuthProvider } from '@react-oauth/google'
import { Check, FileText, Footprints, Search } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { cn } from '@/lib/utils'

type JourneyItem = {
  label: string
  description: string
  icon: LucideIcon
}

const JOURNEY: JourneyItem[] = [
  {
    label: 'Upload your resume',
    description: 'Start with the experience and skills you already have.',
    icon: FileText,
  },
  {
    label: 'Review your profile',
    description: 'Confirm every detail and keep your information up to date.',
    icon: Check,
  },
  {
    label: 'Discover relevant roles',
    description: 'Use a complete profile to focus on opportunities that fit.',
    icon: Search,
  },
]

function ProductJourney() {
  return (
    <ol className="mt-10 space-y-6" aria-label="How Hire Journey works">
      {JOURNEY.map(({ label, description, icon: Icon }) => (
        <li key={label} className="flex gap-4">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-brand-border bg-white text-brand-violet">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-base font-semibold text-brand-ink">{label}</h2>
            <p className="mt-1 text-sm leading-6 text-brand-muted">{description}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const onLogin = pathname?.startsWith('/login')

  const tab = (href: string, label: string, active: boolean) => (
    <Link
      href={href}
      className={cn(
        'flex-1 border-b pb-3 text-center text-base font-semibold transition-colors',
        active
          ? 'border-brand-violet text-brand-violet'
          : 'border-brand-border text-brand-muted hover:border-brand-muted hover:text-brand-ink',
      )}
      aria-current={active ? 'page' : undefined}
    >
      {label}
    </Link>
  )

  return (
    <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!}>
      <div className="flex min-h-screen w-full bg-white">
        <aside className="hidden w-[55%] flex-col justify-between border-r border-brand-border bg-brand-paper p-12 lg:flex xl:p-16">
          <div className="flex items-center gap-2 text-2xl font-semibold text-brand-violet">
            <Footprints className="h-6 w-6" aria-hidden="true" />
            Hire Journey
          </div>

          <div className="my-12 max-w-lg">
            <p className="mb-4 text-sm font-semibold text-brand-violet">A calmer career workspace</p>
            <h1 className="text-4xl font-semibold leading-tight tracking-tight text-brand-ink xl:text-5xl">
              A clearer path through your job search.
            </h1>
            <p className="mt-5 max-w-md text-base leading-7 text-brand-muted">
              Organize your experience, preferences, and opportunities in one focused place.
            </p>
            <ProductJourney />
          </div>

          <p className="flex items-center gap-3 border-t border-brand-border pt-6 text-sm text-brand-muted">
            <Check className="h-5 w-5 shrink-0 text-brand-emerald" aria-hidden="true" />
            Your profile stays editable at every step.
          </p>
        </aside>

        <main className="flex min-h-screen w-full items-center justify-center overflow-y-auto bg-white p-6 md:p-12 lg:w-[45%]">
          <div className="w-full max-w-md py-8">
            <div className="mb-8 flex items-center gap-2 text-2xl font-semibold text-brand-violet lg:hidden">
              <Footprints className="h-6 w-6" aria-hidden="true" />
              Hire Journey
            </div>

            <nav className="mb-8 flex" aria-label="Account access">
              {tab('/register', 'Create account', !onLogin)}
              {tab('/login', 'Sign in', !!onLogin)}
            </nav>

            {children}
          </div>
        </main>
      </div>
    </GoogleOAuthProvider>
  )
}
