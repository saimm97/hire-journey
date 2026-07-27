"use client"

import { AlertTriangle } from "lucide-react"

interface OnboardingLoadErrorProps {
  message: string | null
  onRetry: () => void
}

/**
 * Shown when the initial snapshot fetch fails. Deliberately NOT an empty form:
 * rendering the editable form on a failed load lets a save overwrite stored
 * data with blanks, so we stop and offer a retry instead.
 */
export function OnboardingLoadError({ message, onRetry }: OnboardingLoadErrorProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-brand-border bg-white p-12 text-center shadow-[0_4px_20px_rgba(35,31,28,0.04)]">
      <div className="flex size-14 items-center justify-center rounded-full bg-brand-coral/10 text-brand-coral">
        <AlertTriangle className="size-7" />
      </div>
      <div className="space-y-1">
        <h3 className="text-xl font-semibold tracking-tight text-brand-ink">
          We couldn&apos;t load your details
        </h3>
        <p className="text-brand-muted">
          {message ?? "Something went wrong."} Your saved information is safe.
        </p>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-full bg-brand-coral px-5 py-2.5 font-semibold text-white shadow-sm transition-colors hover:bg-brand-coral-dark"
      >
        Try again
      </button>
    </div>
  )
}
