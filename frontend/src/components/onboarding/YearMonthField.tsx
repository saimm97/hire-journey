"use client"

import { useState } from "react"

import { TextField } from "./TextField"

type DatePrecision = "month" | "year"

const YEAR_RE = /^\d{4}$/
const MONTH_RE = /^\d{4}-(?:0[1-9]|1[0-2])$/

interface YearMonthFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  fieldPath: string
  error?: string
}

/**
 * A native month picker with an explicit year-only mode. Resumes often say
 * only "2021"; preserving that precision avoids silently inventing January.
 */
export function YearMonthField({
  label,
  value,
  onChange,
  fieldPath,
  error,
}: YearMonthFieldProps) {
  const [emptyPrecision, setEmptyPrecision] = useState<DatePrecision>(
    YEAR_RE.test(value) ? "year" : "month",
  )
  const precision = YEAR_RE.test(value)
    ? "year"
    : MONTH_RE.test(value)
      ? "month"
      : emptyPrecision
  const yearOnly = precision === "year"
  const switchPrecision = () => {
    if (yearOnly) {
      setEmptyPrecision("month")
      // A native month input cannot represent a bare year. Clear it so the user
      // deliberately chooses a month instead of us fabricating January.
      if (YEAR_RE.test(value)) onChange("")
      return
    }

    setEmptyPrecision("year")
    if (MONTH_RE.test(value)) onChange(value.slice(0, 4))
  }

  return (
    <TextField
      label={label}
      type={yearOnly ? "text" : "month"}
      inputMode={yearOnly ? "numeric" : undefined}
      pattern={yearOnly ? "\\d{4}" : undefined}
      placeholder={yearOnly ? "YYYY" : undefined}
      mono
      value={value}
      onChange={(nextValue) => {
        // Keep the chosen input visible while the user temporarily has an
        // incomplete value such as "20" or clears it.
        setEmptyPrecision(precision)
        onChange(nextValue)
      }}
      fieldPath={fieldPath}
      error={error}
      badge={
        <button
          type="button"
          onClick={switchPrecision}
          aria-label={`${yearOnly ? "Use month picker" : "Use year only"} for ${label}`}
          className="rounded px-1.5 py-0.5 text-xs font-medium text-brand-primary transition-colors hover:bg-brand-primary/10"
        >
          {yearOnly ? "Use month" : "Year only"}
        </button>
      }
    />
  )
}
