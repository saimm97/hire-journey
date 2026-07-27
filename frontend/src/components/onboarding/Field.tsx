import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface FieldProps {
  label: string
  badge?: ReactNode
  className?: string
  htmlFor?: string
  error?: string
  errorId?: string
  fieldPath?: string
  children: ReactNode
}

/** A label and optional badge above a standardized bordered control. */
export function Field({
  label,
  badge,
  className,
  htmlFor,
  error,
  errorId,
  fieldPath,
  children,
}: FieldProps) {
  const labelClassName = cn(
    "text-sm font-medium leading-5 text-brand-ink",
    error && "text-red-600",
  )

  return (
    <div
      data-field-path={fieldPath}
      tabIndex={fieldPath ? -1 : undefined}
      aria-invalid={fieldPath && error ? true : undefined}
      aria-describedby={fieldPath && error ? errorId : undefined}
      className={cn("space-y-1.5", className)}
    >
      <div className="flex min-h-5 items-center justify-between gap-2">
        {htmlFor ? (
          <label htmlFor={htmlFor} className={labelClassName}>
            {label}
          </label>
        ) : (
          <span className={labelClassName}>{label}</span>
        )}
        {badge}
      </div>
      <div
        className={cn(
          "flex min-h-11 flex-col justify-center rounded-lg border border-brand-border bg-white px-3 py-2 transition-all",
          "focus-within:border-brand-primary focus-within:ring-2 focus-within:ring-brand-primary/20",
          error &&
            "border-red-500 focus-within:border-red-500 focus-within:ring-red-500/20",
        )}
      >
        {children}
      </div>
      {error && (
        <p id={errorId} className="text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  )
}
