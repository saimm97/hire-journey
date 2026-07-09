"use client"

import { X } from "lucide-react"

interface ChipProps {
  value: string
  onRemove: () => void
}

/** A removable pill — the shared "bubble" for selected values across the wizard. */
export function Chip({ value, onRemove }: ChipProps) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-brand-surface px-3 py-1 text-sm text-brand-muted">
      {value}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${value}`}
        className="flex items-center hover:text-brand-ink"
      >
        <X className="size-3.5" />
      </button>
    </span>
  )
}
