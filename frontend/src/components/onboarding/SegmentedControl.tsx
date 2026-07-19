"use client"

import { cn } from "@/lib/utils"

export interface SegmentOption<T extends string = string> {
  value: T
  label: string
}

interface SegmentedControlProps<T extends string> {
  options: SegmentOption<T>[]
  /** The selected value, or null when nothing is chosen. */
  value: T | null
  /** Called with the new value, or null when the active segment is toggled off. */
  onChange: (value: T | null) => void
}

/** A single-select segmented control. Clicking the active segment clears it. */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  return (
    <div role="radiogroup" className="flex gap-1 rounded-lg bg-brand-surface p-1">
      {options.map((option) => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(active ? null : option.value)}
            className={cn(
              "flex-1 rounded-md py-1.5 text-center text-sm transition-colors",
              active
                ? "bg-white font-medium text-brand-ink shadow-sm"
                : "text-brand-muted hover:text-brand-ink",
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
