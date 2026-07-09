"use client"

import { cn } from "@/lib/utils"

interface ToggleProps {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}

/** A labeled pill switch. The label sits left of the track. */
export function Toggle({ label, checked, onChange }: ToggleProps) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm text-brand-muted">
      {label}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative h-6 w-10 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-violet/40",
          checked ? "bg-brand-violet" : "bg-brand-border",
        )}
      >
        <span
          className={cn(
            "absolute top-1 size-4 rounded-full bg-white transition-transform",
            checked ? "translate-x-5" : "translate-x-1",
          )}
        />
      </button>
    </label>
  )
}
