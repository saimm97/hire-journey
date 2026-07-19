import type { ReactNode } from "react"

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
}: TextFieldProps) {
  return (
    <Field label={label} badge={badge} className={className}>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          "w-full border-none bg-transparent p-0 text-brand-ink outline-none placeholder:text-brand-muted/60 focus:ring-0",
          mono ? "font-mono text-sm" : "text-base",
        )}
      />
    </Field>
  )
}
