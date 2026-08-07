"use client"

import { useId, type ReactNode } from "react"
import { Plus, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/** Card frame for one repeatable-section entry, with its remove control. */
export function EditorCard({
  onRemove,
  error,
  fieldPath,
  children,
}: {
  onRemove: () => void
  error?: string
  fieldPath?: string
  children: ReactNode
}) {
  const generatedId = useId()
  const errorId = error ? `${generatedId}-error` : undefined

  return (
    <div
      data-field-path={fieldPath}
      tabIndex={fieldPath ? -1 : undefined}
      aria-invalid={error ? true : undefined}
      aria-describedby={errorId}
      className={cn(
        "relative space-y-3 rounded-lg border border-brand-border bg-brand-paper p-4",
        error && "border-red-500",
      )}
    >
      <button
        type="button"
        onClick={onRemove}
        aria-label="Remove entry"
        className="absolute right-3 top-3 text-brand-muted transition-colors hover:text-red-500"
      >
        <Trash2 className="size-4" />
      </button>
      {error && (
        <p id={errorId} className="pr-8 text-xs text-red-600">
          {error}
        </p>
      )}
      {children}
    </div>
  )
}

/** Dashed add-row button shared by every repeatable editor. */
export function AddItemButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <Button
      type="button"
      onClick={onClick}
      variant="outline"
      size="sm"
      className="border-dashed"
    >
      <Plus className="size-4" /> {label}
    </Button>
  )
}
