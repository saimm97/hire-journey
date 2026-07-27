"use client"

import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react"

interface WizardFooterProps {
  note?: string
  saving: boolean
  onSave: () => void
  /** CTA label; defaults to the profile step's wording. */
  label?: string
  /** Back handler; the button is inert (as before) when omitted. */
  onBack?: () => void
}

/** Sticky onboarding footer: back on the left, the momentum CTA on the right. */
export function WizardFooter({
  note,
  saving,
  onSave,
  label = "Save & continue",
  onBack,
}: WizardFooterProps) {
  return (
    <footer className="fixed inset-x-0 bottom-0 z-40 border-t border-brand-border bg-brand-surface/90 px-6 py-3 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1 rounded-md px-3 py-2 text-sm font-medium text-brand-muted hover:bg-white hover:text-brand-ink"
        >
          <ArrowLeft className="size-4" /> Back
        </button>
        <div className="flex items-center gap-4">
          {note && <span className="hidden text-xs text-brand-muted sm:block">{note}</span>}
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-full bg-brand-coral px-6 py-2.5 font-semibold text-white shadow-sm transition-colors hover:bg-brand-coral-dark disabled:opacity-60"
          >
            {saving ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Saving…
              </>
            ) : (
              <>
                {label} <ArrowRight className="size-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </footer>
  )
}
