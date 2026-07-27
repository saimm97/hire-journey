"use client"

import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface WizardFooterProps {
  note?: string
  saving: boolean
  onSave: () => void
  /** CTA label; defaults to the profile step's wording. */
  label?: string
  /** Back handler; the control is omitted when there is no working destination. */
  onBack?: () => void
}

/** Sticky onboarding footer with a single authoritative primary action. */
export function WizardFooter({
  note,
  saving,
  onSave,
  label = "Save & continue",
  onBack,
}: WizardFooterProps) {
  return (
    <footer className="fixed inset-x-0 bottom-0 z-40 border-t border-brand-border bg-white/95 px-4 py-3 backdrop-blur-md sm:px-6">
      <div
        className={cn(
          "mx-auto flex max-w-5xl items-center gap-4",
          onBack ? "justify-between" : "justify-end",
        )}
      >
        {onBack && (
          <Button type="button" onClick={onBack} variant="ghost">
            <ArrowLeft className="size-4" /> Back
          </Button>
        )}
        <div className="flex items-center gap-4">
          {note && <span className="hidden text-xs text-brand-muted sm:block">{note}</span>}
          <Button type="button" onClick={onSave} disabled={saving} size="lg">
            {saving ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Saving…
              </>
            ) : (
              <>
                {label} <ArrowRight className="size-4" />
              </>
            )}
          </Button>
        </div>
      </div>
    </footer>
  )
}
