"use client"

import type { ReactNode } from "react"

import { JourneySpine, type Milestone } from "./JourneySpine"

interface OnboardingShellProps {
  step: Milestone
  title: string
  subtitle: string
  children: ReactNode
}

/** Shared chrome for the wizard pages: header, journey spine, and title block. */
export function OnboardingShell({ step, title, subtitle, children }: OnboardingShellProps) {
  return (
    <div className="min-h-screen bg-brand-paper">
      <header className="border-b border-brand-border bg-white px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="text-lg font-semibold tracking-tight text-brand-ink">Hire Journey</span>
          <span className="text-xs font-medium text-brand-muted">
            Onboarding
          </span>
        </div>
      </header>
      <JourneySpine current={step} />
      <main className="mx-auto max-w-5xl px-6 py-10 pb-32">
        <div className="mb-8 space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight text-brand-ink">{title}</h1>
          <p className="text-brand-muted">{subtitle}</p>
        </div>
        {children}
      </main>
    </div>
  )
}
