"use client"

import { useId, useState } from "react"
import { Plus, type LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Chip } from "./Chip"

interface MultiSelectProps {
  /** The currently selected values. */
  values: string[]
  /** Add a value. Case-aware de-duplication lives in the caller. */
  onAdd: (value: string) => void
  /** Remove a value by exact match. */
  onRemove: (value: string) => void
  /** Predefined choices, rendered as clickable pills (selected ones drop out). */
  options: string[]
  /** When true, a text input with type-ahead allows values outside `options`. */
  allowCustom?: boolean
  placeholder?: string
  icon?: LucideIcon
  addLabel?: string
}

/**
 * Option-driven multi-select: click a predefined pill or (optionally) type a
 * custom value; chosen values collect as removable bubbles below. Backs both the
 * target-roles and seniority pickers.
 */
export function MultiSelect({
  values,
  onAdd,
  onRemove,
  options,
  allowCustom = false,
  placeholder,
  icon: Icon,
  addLabel = "Add",
}: MultiSelectProps) {
  const [draft, setDraft] = useState("")
  const listId = useId()

  const chosen = new Set(values.map((value) => value.toLowerCase()))
  const available = options.filter((option) => !chosen.has(option.toLowerCase()))

  const commit = () => {
    onAdd(draft)
    setDraft("")
  }

  return (
    <div className="space-y-3">
      {allowCustom && (
        <div className="relative">
          {Icon && (
            <Icon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-brand-muted" />
          )}
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault()
                commit()
              }
            }}
            placeholder={placeholder}
            list={listId}
            aria-label={addLabel}
            className={cn(
              "h-11 w-full rounded-lg border border-brand-border bg-white py-2 pr-3 text-brand-ink outline-none transition-all",
              "placeholder:text-brand-muted/60 focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/20",
              Icon ? "pl-9" : "pl-3",
            )}
          />
          <datalist id={listId}>
            {available.map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
        </div>
      )}

      {available.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {available.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => onAdd(option)}
              className="inline-flex items-center gap-1 rounded-full border border-brand-border bg-white px-3 py-1 text-sm text-brand-muted transition-colors hover:border-brand-primary/60 hover:text-brand-ink"
            >
              <Plus className="size-3.5" /> {option}
            </button>
          ))}
        </div>
      )}

      {values.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {values.map((value) => (
            <Chip key={value} value={value} onRemove={() => onRemove(value)} />
          ))}
        </div>
      )}
    </div>
  )
}
