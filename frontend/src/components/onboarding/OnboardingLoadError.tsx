"use client"

import { AlertTriangle } from "lucide-react"

import { Button } from "@/components/ui/button"

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
    <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-brand-border bg-white p-8 text-center sm:p-12">
      <div className="flex size-14 items-center justify-center rounded-full bg-red-50 text-red-700">
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
      <Button type="button" onClick={onRetry} size="lg">
        Try again
      </Button>
    </div>
  )
}
