"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import type { ReactNode } from "react"
import {
  LayoutGrid,
  LogOut,
  User,
  type LucideIcon,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth/AuthContext"
import { cn } from "@/lib/utils"

interface NavItem {
  label: string
  icon: LucideIcon
  href: string
}

const NAV: NavItem[] = [
  { label: "Dashboard", icon: LayoutGrid, href: "/dashboard" },
  { label: "Profile", icon: User, href: "/profile" },
]

const ITEM =
  "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors"

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuth()

  async function handleLogout() {
    await logout()
    router.replace("/login")
  }

  const navigation = (placement: "desktop" | "mobile") => (
    <nav
      aria-label={placement === "desktop" ? "Primary navigation" : "Mobile navigation"}
      className={placement === "desktop" ? "mt-8 space-y-1" : "flex gap-1 overflow-x-auto"}
    >
      {NAV.map(({ label, icon: Icon, href }) => {
        const active = pathname.startsWith(href)
        return (
          <Link
            key={`${placement}-${label}`}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              ITEM,
              placement === "mobile" && "shrink-0",
              active
                ? "bg-brand-violet/10 text-brand-violet"
                : "text-brand-muted hover:bg-brand-surface hover:text-brand-ink",
            )}
          >
            <Icon className="size-4" /> {label}
          </Link>
        )
      })}
    </nav>
  )

  return (
    <div className="min-h-screen bg-brand-paper lg:flex">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-brand-border bg-white px-4 py-6 lg:flex">
        <div className="px-2">
          <p className="text-lg font-semibold tracking-tight text-brand-violet">Hire Journey</p>
          <p className="mt-0.5 text-xs text-brand-muted">Career workspace</p>
        </div>

        {navigation("desktop")}

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
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={handleLogout}
            title="Log out"
            aria-label="Log out"
            className="shrink-0 hover:text-destructive"
          >
            <LogOut className="size-4" />
          </Button>
        </div>
      </aside>

      <header className="sticky top-0 z-30 border-b border-brand-border bg-white/95 backdrop-blur lg:hidden">
        <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
          <p className="min-w-0 flex-1 text-lg font-semibold tracking-tight text-brand-violet">
            Hire Journey
          </p>
          <span className="max-w-32 truncate text-sm font-medium text-brand-ink">
            {user?.username ?? "…"}
          </span>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={handleLogout}
            title="Log out"
            aria-label="Log out"
            className="hover:text-destructive"
          >
            <LogOut className="size-4" />
          </Button>
        </div>
        <div className="border-t border-brand-border px-4 py-2 sm:px-6">
          {navigation("mobile")}
        </div>
      </header>

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-10">{children}</main>
    </div>
  )
}
