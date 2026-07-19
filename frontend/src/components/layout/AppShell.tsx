import Link from "next/link"
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

const NAV = [
  { key: "dashboard", href: "/dashboard", label: "Dashboard" },
  { key: "profile", href: "/profile", label: "Profile" },
] as const

interface AppShellProps {
  active: (typeof NAV)[number]["key"]
  children: ReactNode
}

/** Post-onboarding app chrome: brand header with top-level navigation. */
export function AppShell({ active, children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-brand-paper">
      <header className="border-b border-brand-border bg-white px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="font-display text-lg font-semibold text-brand-ink">Hire Journey</span>
          <nav className="flex items-center gap-5">
            {NAV.map((item) => (
              <Link
                key={item.key}
                href={item.href}
                className={cn(
                  "font-mono text-[11px] uppercase tracking-wide transition-colors",
                  active === item.key
                    ? "font-bold text-brand-ink"
                    : "text-brand-muted hover:text-brand-ink",
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-10 pb-24">{children}</main>
    </div>
  )
}
