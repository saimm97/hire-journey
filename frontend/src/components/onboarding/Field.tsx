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

/** A bordered input frame with the label and an optional badge stacked above the control. */
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
      className={cn(
        "rounded-lg border border-brand-border bg-white px-3 py-2 transition-all",
        "focus-within:border-brand-violet focus-within:ring-2 focus-within:ring-brand-violet/20",
        error &&
          "border-red-500 focus-within:border-red-500 focus-within:ring-red-500/20",
        className,
      )}
    >
      <div className="mb-1 flex items-center justify-between">
        {htmlFor ? (
          <label htmlFor={htmlFor} className={labelClassName}>
            {label}
          </label>
        ) : (
          <span className={labelClassName}>{label}</span>
        )}
        {badge}
      </div>
      {children}
      {error && (
        <p id={errorId} className="mt-1 text-xs text-red-600">
          {error}
        </p>
      )}
    </div>
  )
}
