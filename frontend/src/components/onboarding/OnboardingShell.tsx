"use client"

import type { ReactNode } from "react"

import { JourneySpine, type OnboardingStep } from "./JourneySpine"

interface OnboardingShellProps {
  step: OnboardingStep | null
  completedSteps?: OnboardingStep[]
  title: string
  subtitle: string
  children: ReactNode
}

/** Shared chrome for the wizard pages: header, journey spine, and title block. */
export function OnboardingShell({
  step,
  completedSteps,
  title,
  subtitle,
  children,
}: OnboardingShellProps) {
  return (
    <div className="min-h-screen bg-brand-paper">
      <header className="border-b border-brand-border bg-white px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="text-lg font-semibold tracking-tight text-brand-ink">Hire Journey</span>
          <span className="text-sm font-medium text-brand-muted">Onboarding</span>
        </div>
      </header>
      <JourneySpine current={step} completed={completedSteps} />
      <main className="mx-auto max-w-5xl px-4 py-8 pb-32 sm:px-6 sm:py-10">
        <div className="mb-8 space-y-2">
          <h1 className="text-[32px] font-semibold leading-10 tracking-tight text-brand-ink">{title}</h1>
          <p className="text-brand-muted">{subtitle}</p>
        </div>
        {children}
      </main>
    </div>
  )
}
