import { useId, type ReactNode } from "react"

import { cn } from "@/lib/utils"
import { Field } from "./Field"

interface TextFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  placeholder?: string
  badge?: ReactNode
  mono?: boolean
  className?: string
  fieldPath?: string
  error?: string
  inputMode?: "text" | "numeric" | "decimal" | "tel" | "email" | "url" | "search" | "none"
  pattern?: string
}

/** A labeled, borderless text input inside a {@link Field} frame. */
export function TextField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  badge,
  mono,
  className,
  fieldPath,
  error,
  inputMode,
  pattern,
}: TextFieldProps) {
  const generatedId = useId()
  const inputId = fieldPath ? `field-${fieldPath}` : generatedId
  const errorId = error ? `${inputId}-error` : undefined

  return (
    <Field
      label={label}
      badge={badge}
      className={className}
      htmlFor={inputId}
      error={error}
      errorId={errorId}
    >
      <input
        id={inputId}
        name={fieldPath}
        data-field-path={fieldPath}
        type={type}
        inputMode={inputMode}
        pattern={pattern}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
        className={cn(
          "w-full border-none bg-transparent p-0 text-brand-ink outline-none placeholder:text-brand-muted/60 focus:ring-0",
          mono ? "font-mono text-sm" : "text-base",
        )}
      />
    </Field>
  )
}
