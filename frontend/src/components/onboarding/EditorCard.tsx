"use client"

import type { ReactNode } from "react"
import { Plus, Trash2 } from "lucide-react"

/** Card frame for one repeatable-section entry, with its remove control. */
export function EditorCard({ onRemove, children }: { onRemove: () => void; children: ReactNode }) {
  return (
    <div className="relative space-y-3 rounded-xl border border-brand-border bg-white p-4">
      <button
        type="button"
        onClick={onRemove}
        aria-label="Remove entry"
        className="absolute right-3 top-3 text-brand-muted transition-colors hover:text-red-500"
      >
        <Trash2 className="size-4" />
      </button>
      {children}
    </div>
  )
}

/** Dashed add-row button shared by every repeatable editor. */
export function AddItemButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-lg border border-dashed border-brand-border px-3 py-2 text-sm text-brand-muted transition-colors hover:border-brand-violet/60 hover:text-brand-ink"
    >
      <Plus className="size-4" /> {label}
    </button>
  )
}
