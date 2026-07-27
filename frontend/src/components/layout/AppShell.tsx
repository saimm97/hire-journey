"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import type { ReactNode } from "react"
import {
  Briefcase,
  FileText,
  LayoutGrid,
  LogOut,
  Plus,
  Search,
  Sparkles,
  User,
  type LucideIcon,
} from "lucide-react"

import { useAuth } from "@/lib/auth/AuthContext"
import { cn } from "@/lib/utils"

interface NavItem {
  label: string
  icon: LucideIcon
  /** Absent while the section doesn't exist yet — rendered muted and inert. */
  href?: string
}

const NAV: NavItem[] = [
  { label: "Dashboard", icon: LayoutGrid, href: "/dashboard" },
  { label: "Search", icon: Search },
  { label: "Matches", icon: Sparkles },
  { label: "Applications", icon: Briefcase },
  { label: "Documents", icon: FileText },
  { label: "Profile", icon: User, href: "/profile" },
]

const ITEM = "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuth()

  async function handleLogout() {
    await logout()
    router.replace("/login")
  }

  return (
    <div className="flex min-h-screen bg-brand-paper">
      <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-brand-border bg-brand-surface px-4 py-6">
        <div className="px-2">
          <p className="text-lg font-semibold tracking-tight text-brand-violet">Hire Journey</p>
          <p className="text-xs font-medium text-brand-muted">
            AI Copilot
          </p>
        </div>

        <button
          type="button"
          disabled
          title="Coming soon"
          className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-full bg-brand-violet px-4 py-2.5 text-sm font-semibold text-white opacity-50 shadow-sm"
        >
          <Plus className="size-4" /> Start New Search
        </button>

        <nav className="mt-6 space-y-1">
          {NAV.map(({ label, icon: Icon, href }) =>
            href ? (
              <Link
                key={label}
                href={href}
                className={cn(
                  ITEM,
                  pathname.startsWith(href)
                    ? "bg-brand-violet/10 font-medium text-brand-violet"
                    : "text-brand-muted hover:bg-white hover:text-brand-ink",
                )}
              >
                <Icon className="size-4" /> {label}
              </Link>
            ) : (
              <span
                key={label}
                title="Coming soon"
                className={cn(ITEM, "cursor-default text-brand-muted/50")}
              >
                <Icon className="size-4" /> {label}
              </span>
            ),
          )}
        </nav>

        <div className="mt-auto flex items-center gap-3 border-t border-brand-border px-2 pt-4">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand-violet/10 font-semibold text-brand-violet">
            {user?.username?.[0]?.toUpperCase() ?? "?"}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-brand-ink">
              {user?.username ?? "…"}
            </span>
            <span className="block truncate text-xs text-brand-muted">{user?.email}</span>
          </span>
          <button
            type="button"
            onClick={handleLogout}
            title="Log out"
            aria-label="Log out"
            className="shrink-0 rounded-lg p-2 text-brand-muted transition-colors hover:bg-white hover:text-brand-coral"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-10 py-10">{children}</main>
    </div>
  )
}
