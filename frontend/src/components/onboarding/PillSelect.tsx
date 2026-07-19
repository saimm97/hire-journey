"use client"

import { cn } from "@/lib/utils"

export interface PillOption<T extends string = string> {
  value: T
  label: string
}

interface PillSelectProps<T extends string> {
  options: PillOption<T>[]
  value: T | null
  onChange: (value: T | null) => void
}

/** Single-select wrapping pills — for enums too wide for a SegmentedControl. */
export function PillSelect<T extends string>({ options, value, onChange }: PillSelectProps<T>) {
  return (
    <div role="radiogroup" className="flex flex-wrap gap-2">
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
              "rounded-full border px-3 py-1 text-sm transition-colors",
              active
                ? "border-brand-violet bg-brand-violet/10 font-medium text-brand-ink"
                : "border-brand-border bg-white text-brand-muted hover:border-brand-violet/60 hover:text-brand-ink",
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
