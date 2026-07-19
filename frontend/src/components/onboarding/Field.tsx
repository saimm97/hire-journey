import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface FieldProps {
  label: string
  badge?: ReactNode
  className?: string
  children: ReactNode
}

/** A bordered input frame with the label and an optional badge stacked above the control. */
export function Field({ label, badge, className, children }: FieldProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-brand-border bg-white px-3 py-2 transition-all",
        "focus-within:border-brand-violet focus-within:ring-2 focus-within:ring-brand-violet/20",
        className,
      )}
    >
      <div className="mb-1 flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase tracking-wide text-brand-muted">{label}</span>
        {badge}
      </div>
      {children}
    </div>
  )
}
