"use client"

const STEP = 5_000

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
})

interface SalaryFieldProps {
  /** The minimum acceptable base salary, or null when unset. */
  value: number | null
  onChange: (value: number | null) => void
}

/** Minimum-salary number input (maps to minimum_salary). */
export function SalaryField({ value, onChange }: SalaryFieldProps) {
  return (
    <div className="space-y-2">
      <label htmlFor="minimum-salary" className="block text-sm text-brand-muted">
        Minimum acceptable (base)
      </label>
      <div className="relative max-w-[200px]">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono text-sm text-brand-muted">
          $
        </span>
        <input
          id="minimum-salary"
          type="number"
          inputMode="numeric"
          min={0}
          step={STEP}
          value={value ?? ""}
          placeholder="120000"
          onChange={(event) =>
            onChange(event.target.value === "" ? null : Number(event.target.value))
          }
          className="w-full rounded-lg border border-brand-border bg-white py-2 pl-7 pr-3 font-mono text-sm text-brand-ink outline-none transition-all placeholder:text-brand-muted/60 focus:border-brand-violet focus:ring-2 focus:ring-brand-violet/20"
        />
      </div>
      <p className="text-sm text-brand-muted">
        {value == null ? (
          "Set a minimum to focus your matches (optional)."
        ) : (
          <>
            Targeting:{" "}
            <span className="font-mono font-medium text-brand-ink">{currency.format(value)}</span>
          </>
        )}
      </p>
    </div>
  )
}
