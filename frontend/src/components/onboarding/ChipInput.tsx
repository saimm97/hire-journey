"use client"

import { useId, useState } from "react"
import { Plus, type LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Chip } from "./Chip"

interface ChipInputProps {
  /** The current chips. */
  values: string[]
  /** Add a chip. De-duplication lives in the caller so it can be case-aware. */
  onAdd: (value: string) => void
  /** Remove a chip by exact value. */
  onRemove: (value: string) => void
  placeholder?: string
  /** Optional type-ahead options, surfaced via a native datalist. */
  suggestions?: string[]
  /** Optional icon inside the input (stacked layout only). */
  icon?: LucideIcon
  /**
   * "stacked": a full-width input above the chips (roles, locations).
   * "inline": a compact add-box that sits among the chips (skills).
   */
  layout?: "stacked" | "inline"
  /** Accessible label for the add control. */
  addLabel?: string
}

/**
 * Removable chips plus an add-input with optional type-ahead. The single source
 * of chip UI across the wizard: skills, target roles, and locations all use it.
 */
export function ChipInput({
  values,
  onAdd,
  onRemove,
  placeholder,
  suggestions,
  icon: Icon,
  layout = "stacked",
  addLabel = "Add",
}: ChipInputProps) {
  const [draft, setDraft] = useState("")
  const listId = useId()

  const commit = () => {
    onAdd(draft)
    setDraft("")
  }

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault()
      commit()
    }
  }

  const datalist = suggestions?.length ? (
    <datalist id={listId}>
      {suggestions.map((option) => (
        <option key={option} value={option} />
      ))}
    </datalist>
  ) : null

  const chips = values.map((value) => (
    <Chip key={value} value={value} onRemove={() => onRemove(value)} />
  ))

  if (layout === "inline") {
    return (
      <div className="flex flex-wrap gap-2">
        {chips}
        <div className="inline-flex items-center rounded-full border border-brand-border bg-white px-3 py-1 focus-within:border-brand-violet focus-within:ring-2 focus-within:ring-brand-violet/20">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder={placeholder}
            list={suggestions?.length ? listId : undefined}
            aria-label={addLabel}
            className="w-24 border-none bg-transparent p-0 text-sm text-brand-ink outline-none placeholder:text-brand-muted/60 focus:ring-0"
          />
          <button
            type="button"
            onClick={commit}
            aria-label={addLabel}
            className="flex items-center text-brand-muted hover:text-brand-violet"
          >
            <Plus className="size-4" />
          </button>
          {datalist}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="relative">
        {Icon && (
          <Icon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-brand-muted" />
        )}
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          list={suggestions?.length ? listId : undefined}
          aria-label={addLabel}
          className={cn(
            "w-full rounded-lg border border-brand-border bg-white py-2 pr-3 text-brand-ink outline-none transition-all",
            "placeholder:text-brand-muted/60 focus:border-brand-violet focus:ring-2 focus:ring-brand-violet/20",
            Icon ? "pl-9" : "pl-3",
          )}
        />
        {datalist}
      </div>
      {values.length > 0 && <div className="flex flex-wrap gap-2">{chips}</div>}
    </div>
  )
}
