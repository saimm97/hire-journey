import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface SectionProps {
  title: string
  action?: ReactNode
  fieldPath?: string
  error?: string
  children: ReactNode
}

/** A titled block: a mono uppercase heading with an optional right-aligned action. */
export function Section({ title, action, fieldPath, error, children }: SectionProps) {
  const errorId = fieldPath && error ? `section-${fieldPath}-error` : undefined

  return (
    <section
      className={cn("space-y-4", error && "rounded-lg border border-red-500 p-3")}
      data-field-path={fieldPath}
      tabIndex={fieldPath ? -1 : undefined}
      aria-describedby={errorId}
    >
      <div className="flex items-center justify-between">
        <h3
          className={cn(
            "text-xl font-semibold leading-7 tracking-tight text-brand-ink",
            error && "text-red-600",
          )}
        >
          {title}
        </h3>
        {action}
      </div>
      {error && (
        <p id={errorId} className="text-xs text-red-600">
          {error}
        </p>
      )}
      {children}
    </section>
  )
}
